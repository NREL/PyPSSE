# --------------------------------------------------------------------------------------------------
# DC-AC Tool: main function
# Bin Wang
# 4/28/2022
#
# Reference:
# Wang, Bin, and Jin Tan. 2022. DC-AC Tool: Fully Automating the Acquisition of AC Power Flow
# Solution. Golden, CO: National Renewable Energy Laboratory. NREL/TP-6A40-80100.
# https://www.nrel.gov/docs/fy22osti/80100.pdf
# --------------------------------------------------------------------------------------------------


import random

import numpy as np
from loguru import logger

from pypsse.utils.dc2ac.helper_functions import PowerFlowData


class DC2ACconverter:
    min_kv_filter = 200.0
    filter_buses = 1.0

    def __init__(self, psse, solver, settings, raw_data) -> None:
        self.settings = settings
        self.raw_data = raw_data
        self.solver = solver
        self.psse = psse
        self._f = psse._f
        self._i = psse._i
        self._s = psse._s
        self.converged = False

    def run(self):
        self.pfd = PowerFlowData(self.psse)  # original power flow data
        self.pfdt = PowerFlowData(self.psse)
        self.all_subs = self.get_bus_list()

        self.pfd.getdata()  # get power flow data
        solved_flag = self.if_solved(1, 5)  ## Step 1
        self.sol_out_orig(solved_flag)

        # if directly solved, save the solved case and move to the next
        logger.info(f"solved_flag:{solved_flag}")
        if solved_flag == 0:  ## IF-1, yes
            self.converged = True
            return

        ## IF-1, no
        # try to solve the unsolved AC power flow
        # add generators
        ad_pq_busid, ad_pv_busid = self.add_generators()  ## Step 2

        # solve 1st power flow
        solved_flag_1st = self.if_solved(0, 5)  ## Step 3, IF-2

        # if 1st power flow not converging, check solvability
        if solved_flag_1st:  ## IF-2, no
            logger.info("First power flow (with added generators) cannot converge! Investigating solvability...")
            self.solver.reload()
            insolvable_flag, dec_perc = self.svblt_check()  ## Step 4 - Step 6

            if insolvable_flag == 1:  # still cannot solve  ## Possibility c,
                self.converged = False
                return

            # try to approach the target loading
            step2_tempcase = self.save_raw(4, 2)
            inc_cur, inc_target, inc_step = self.approach_target_loading(dec_perc, step2_tempcase)  ## Step 5

            # Recover the original loading and dispatch
            if inc_cur >= inc_target:
                solved_flag_1st = 0
                # recover loading
                self.psse.read(0, step2_tempcase)  # saveRaw outputs .raw files only
                self.pfdt.getdata(self.psse)

                self.psse.scal_2(0, 1, 1, [0, 0, 0, 0, 0], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                self.psse.scal_2(
                    0,
                    1,
                    2,
                    [self._i, 1, 0, 1, 0],
                    [
                        self.pfd.load_mw_total,
                        self.pfdt.gen_mw_total / self.pfdt.load_mw_total * self.pfd.load_mw_total,
                        0.0,
                        -0.0,
                        0.0,
                        -0.0,
                        self._f,
                    ],
                )
                self.psse.fnsl([0, 0, 0, 1, 1, 0, 0, 0])

                solved_flag = self.if_solved(self.psse, 1, 5)

                if solved_flag:
                    logger.info("Should have solved the case.\n")
                    self.converged = True
                    return
                else:
                    self.psse.rawd_2(0, 1, [1, 1, 1, 0, 0, 0, 0], 0, step2_tempcase)

                # recover dispatch
                if solved_flag == 0:
                    for i in range(len(self.pfd.gen_mw)):
                        busi = self.pfd.bus_num.index(self.pfd.gen_bus[i])

                        if self.pfd.gen_status[i] != 1 or abs(self.pfd.bus_type[busi]) != 2:
                            continue

                        self.psse.read(0, step2_tempcase)
                        self.psse.machine_chng_2(
                            self.pfd.gen_bus[i],
                            self.pfd.gen_id[i],
                            [self._i, self._i, self._i, self._i, self._i, self._i],
                            [
                                self.pfd.gen_mw[i],
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                                self._f,
                            ],
                        )
                        self.psse.fnsl([0, 0, 0, 1, 1, 0, 0, 0])
                        solved_flag = self.if_solved(self.psse, 1, 5)

                        if solved_flag == 0:
                            self.psse.rawd_2(0, 1, [1, 1, 1, 0, 0, 0, 0], 0, step2_tempcase)  ## Possibility b
                        else:
                            logger.info("Should not see this!!!\n")
                            pass

            else:
                inc_cur = inc_cur - inc_step
                perc = str(inc_cur / inc_target * 100)[0:7]
                self.psse.read(0, step2_tempcase)

                self.save_raw(3, 2.1, perc)

                logger.info(
                    "PF (w added gens) not converge, but can converged at %" + perc + " loading. (Failed!)\n"
                )  ## Possibility c
                self.converged = False
                return

        ## IF-2, yes
        # if 1st power flow converges, try to remove added generators
        w_q_bus = []
        w_q_q = []
        if solved_flag_1st == 0:
            logger.info("PF (w added gens) converged.")
            step3_tempcase = self.save_raw(4, 3)

            # try to gradually remove all added generators
            # gen data from PSSE
            self.pfdt.getdata()
            ad_pq_genbus, ad_pq_gen_q, ad_pq_gen_q_abs, ad_pv_genbus, ad_pv_gen_q = self.get_added_generators(
                self.pfdt, ad_pq_busid, ad_pv_busid
            )

            logger.info("Trying to remove added generators..")
            # remove added gen
            n_ct_pv, n_ct_pq, idx = self.remove_added_generators(
                ad_pv_genbus, ad_pq_genbus, ad_pq_gen_q_abs, step3_tempcase
            )  ## Step 7

            # all added gens can be removed  ## IF-8
            if n_ct_pq == len(idx):  ## IF-8, yes
                logger.info("Orig PF converged at target loading. (Success!)\n")
                self.converged = True
                return

            ## IF-7, no
            # added gen cannot be removed completely
            # get Q at unremovable added gen
            ad_genbus, ad_gen_q = self.get_q_of_added_generator(step3_tempcase, ad_pq_busid, ad_pv_busid)

            # voltage adjustment to remove more added gen (directly solved by NR with a better initial)
            step4_tempcase = self.save_raw(5)
            q_remote, bus_remote, v_set_remote = self.remove_geni_adj_vi(ad_genbus, ad_gen_q, step4_tempcase)

            if len(bus_remote) == 0:
                logger.info("Orig PF converged (w adjusted local v_set). (Success!)\n")
                self.save_raw(1, 2)  ## Possibility e
                self.converged = True
                return

            # near-by PV bus voltage adjustment to remove even more added gen
            step5_tempcase = self.save_raw(5)
            self.pfdt.getdata()

            v_set = []
            v_bus = []
            for busi, qi, vseti in zip(bus_remote, q_remote, v_set_remote):
                nearpv, n_layer = self.get_near_pv(busi, 3)

                flag = 2
                for busj in nearpv:
                    gen_online = 0
                    last_found = -1
                    while busj in self.pfdt.gen_bus[last_found + 1 :]:
                        last_found = self.pfdt.gen_bus.index(busj, last_found + 1)
                        if last_found == -1:
                            break
                        else:
                            if self.pfdt.gen_status[last_found] == 1:
                                gen_online = 1

                    if gen_online == 1:
                        vj_set, flag_temp = self.remove_geni_adj_vj(busi, busj, step5_tempcase, vseti)
                    else:
                        continue

                    if flag_temp == 0:
                        flag = 0
                        v_bus.append(busj)
                        v_set.append(vj_set)
                        break

                if flag == 2:
                    w_q_bus.append(busi)
                    w_q_q.append(qi)

        if len(w_q_bus) == 0:
            logger.info("Orig PF converged (w adjusted remote v_set). (Success!)\n")
            self.save_raw(1, 2)  ## Possibility e
            self.converged = True
            return

        else:
            logger.info(
                "PF converged only when w Q support. "
                + str(len(w_q_bus))
                + " out of "
                + str(len(ad_pq_genbus) + len(ad_pv_genbus))
                + " left. \n"
            )
            self.save_raw(2)

            self.converged = True
            return

    @property
    def has_converged(self):
        return self.converged

    def save_raw(self, rawfile, option, option2=0, perc=0):
        # TODO: make changes here
        outfile = str(rawfile)
        if option == 1:
            outfile = outfile.replace("input", "dc2ac_output\\solved")
            if option2 == 1:
                outfile = outfile[0 : len(outfile) - 4] + """_solved.raw"""
            elif option2 == 2:
                outfile = outfile[0 : len(outfile) - 4] + """_addgen_remgen_solved.raw"""

        elif option == 2:
            outfile = outfile.replace("input", "dc2ac_output\\solvedwQ")
            outfile = outfile[0 : len(outfile) - 4] + """_step3_addgen_solved.raw"""

        elif option == 3:
            outfile = outfile.replace("input", "dc2ac_output\\unsolved")
            if option2 == 2:
                outfile = outfile[0 : len(outfile) - 4] + """_step2_addgen_unsolved.raw"""
            elif option2 == 2.1:
                outfile = outfile[0 : len(outfile) - 4] + """_step2_addgen_solved_""" + perc + """.raw"""

        elif option == 4:
            outfile = outfile.replace("input", "temp")
            if option2 == 1:
                outfile = outfile[0 : len(outfile) - 4] + """_step1_addgen.raw"""
            elif option2 == 2:
                outfile = outfile[0 : len(outfile) - 4] + """_step2_addgen_redP.raw"""
            elif option2 == 2.1:
                outfile = outfile[0 : len(outfile) - 4] + """_step2_addgen_solved.raw"""
            elif option2 == 3:
                outfile = outfile[0 : len(outfile) - 4] + """_step3_addgen_remgen.raw"""

        elif option == 5:
            outfile = outfile.replace("input", "dc2ac_output\\solved_Vadju")
            outfile = outfile[0 : len(outfile) - 4] + """_step4_unlimQ.raw"""

        self.psse.rawd_2(0, 1, [1, 1, 1, 0, 0, 0, 0], 0, outfile)

        return outfile

    def if_solved(self, option, n_flag1_max):
        if option == 1:
            self.psse.fnsl([0, 0, 0, 1, 1, 0, 0, 0])
        else:
            self.psse.fnsl([0, 0, 0, 1, 1, 1, 0])  # NR with flat start
        solved_flag = self.psse.solved()

        n_flag1 = 0
        while solved_flag == 1:
            n_flag1 = n_flag1 + 1
            if option == 1:
                self.psse.nsol([0, 0, 0, 1, 1, 0, 0])  # fast decouple with "Do not flat start"
            else:
                self.psse.fnsl([0, 0, 0, 1, 1, 0, 0, 0])
            solved_flag = self.psse.solved()
            if n_flag1 > n_flag1_max:
                logger.info("Flag = 1 does not disappear over " + str(n_flag1_max) + " runs. Let Flag = 2.")
                solved_flag = 2
        return solved_flag

    def add_generators(self):
        ad_pq_busid = []
        ad_pv_busid = []
        for ii in self.all_subs:
            bus_i = self.pfd.bus_num.index(ii)
            bus_i_type = self.pfd.bus_type[bus_i]

            if bus_i_type == 1:
                ad_pq_busid.append(ii)
                self.psse.bus_chng_3(
                    ii,
                    [2, self._i, self._i, self._i],
                    [self._f, 1.000, self._f, self._f, self._f, self._f, self._f],
                    self._s,
                )
                self.psse.plant_data(ii, self._i, [1.000, self._f])
                self.psse.machine_data_2(
                    ii,
                    r"""ad""",
                    [self._i, self._i, self._i, self._i, self._i, self._i],
                    [
                        self._f,
                        self._f,
                        99999.0,
                        -99999.0,
                        99999.0,
                        -99999.0,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                    ],
                )
            if bus_i_type == 2:
                ad_pv_busid.append(ii)
                self.psse.bus_chng_3(
                    ii,
                    [2, self._i, self._i, self._i],
                    [self._f, self._f, self._f, self._f, self._f, self._f, self._f],
                    self._s,
                )
                self.psse.machine_data_2(
                    ii,
                    r"""ad""",
                    [self._i, self._i, self._i, self._i, self._i, self._i],
                    [
                        self._f,
                        self._f,
                        99999.0,
                        -99999.0,
                        99999.0,
                        -99999.0,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                    ],
                )
        return (ad_pq_busid, ad_pv_busid)

    def svblt_check(self):
        # step 1: get a solvable case by reducing the loading
        dec_perc0 = float(0)
        dec_inc = float(5)
        dec_perc = dec_perc0
        n_iter = 0
        n_iter_max = 4
        solved_flag = 1

        insolvable_flag = 0
        while (solved_flag != 0) & (n_iter < n_iter_max):
            n_iter = n_iter + 1
            dec_perc = dec_perc + dec_inc

            # early termination
            if dec_perc >= 10:
                insolvable_flag = 1
                break

            new_load_mw = (100 - dec_perc) / 100 * self.pfd.load_mw_total
            nnew_load_mvar = (100 - dec_perc) / 100 * self.pfd.load_Mvar_total
            new_gen_mw = (100 - dec_perc) / 100 * self.pfd.gen_mw_total

            self.solver.reload()

            self.psse.scal_2(0, 1, 1, [0, 0, 0, 0, 0], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            self.psse.scal_2(
                0, 1, 2, [self.psse._i, 1, 0, 1, 0], [new_load_mw, new_gen_mw, 0.0, -0.0, 0.0, -0.0, nnew_load_mvar]
            )

            self.psse.fnsl([0, 0, 0, 1, 1, 1, 99, 0])
            solved_flag = self.psse.solved()
        if insolvable_flag == 1:
            logger.info("Power flow cannot converge above " + str(100 - dec_perc) + "% loading.\n")
        return insolvable_flag, dec_perc

    def approach_target_loading(self, dec_perc, step2_tempcase):
        inc_target = 100 / (100 - float(dec_perc))
        inc_cur = 1.0001
        inc_step = 0.01
        inc_step_mw = self.pfd.gen_mw_total / inc_target * inc_cur * inc_step
        inc_step_mw_min = float(1)

        pfdt = PowerFlowData(self.psse)

        self.psse.read(0, step2_tempcase)
        pfdt.getdata(self.psse)

        for i in range(len(pfdt.gen_bus)):
            busi = pfdt.bus_num.index(pfdt.gen_bus[i])
            if pfdt.bus_type[busi] == 3 and pfdt.gen_status[i] == 1:
                pfdt.gen_mw_total = pfdt.gen_mw_total - pfdt.gen_mw[i]

        load_mw_pre = pfdt.load_mw_total
        gen_mw_pre = pfdt.gen_mw_total

        while (inc_cur < inc_target) & (inc_step_mw > inc_step_mw_min):
            inc_cur = inc_cur + inc_step
            self.psse.read(0, step2_tempcase)

            gen_mw = gen_mw_pre * inc_cur
            load_mw = load_mw_pre * inc_cur

            for i in range(len(pfdt.gen_bus)):
                busi = pfdt.bus_num.index(pfdt.gen_bus[i])
                if pfdt.bus_type[busi] == 3 and pfdt.gen_status[i] == 1:
                    self.psse.machine_chng_2(
                        pfdt.gen_bus[i],
                        pfdt.gen_id[i],
                        [self._i, self._i, self._i, self._i, self._i, self._i],
                        [
                            0.0,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                            self._f,
                        ],
                    )
            self.psse.scal_2(0, 1, 1, [0, 0, 0, 0, 0], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            self.psse.scal_2(0, 1, 2, [self._i, 1, 0, 1, 0], [load_mw, gen_mw, 0.0, -0.0, 0.0, -0.0, self._f])

            solved_flag = self.if_solved(1, 5)
            if solved_flag == 0:
                self.psse.rawd_2(0, 1, [1, 1, 1, 0, 0, 0, 0], 0, step2_tempcase)
            else:
                inc_cur = inc_cur - inc_step
                inc_step = inc_step / 2
            inc_step_mw = load_mw_pre * inc_step

        return inc_cur, inc_target, inc_step

    def remove_added_generators(self, ad_pv_genbus, ad_pq_genbus, ad_pq_gen_q_abs, step3_tempcase):
        # remove added gen on original pv bus
        n_ct_pv = 0
        for ii in ad_pv_genbus:
            self.psse.read(0, step3_tempcase)
            self.psse.purgmac(ii, r"""ad""")

            solved_flag = self.ifsolved(self.psse, 1, 3)

            if solved_flag == 0:
                n_ct_pv = n_ct_pv + 1
                self.psse.rawd_2(0, 1, [1, 1, 1, 0, 0, 0, 0], 0, step3_tempcase)
            if solved_flag == 2:
                break

        # remove added gen on original pq bus
        idx = sorted(range(len(ad_pq_gen_q_abs)), key=lambda k: ad_pq_gen_q_abs[k])
        n_ct_pq = 0
        n_step = 32
        n_cur = 0
        n_max = len(idx)
        while True:
            if n_step == 0:
                break
            if n_cur + n_step > n_max:
                n_step = n_max - n_cur

            self.psse.read(0, step3_tempcase)
            for nn in range(n_cur, n_cur + n_step, 1):
                ii = idx[nn]
                self.psse.purgmac(ad_pq_genbus[ii], r"""ad""")
                self.psse.bus_chng_3(
                    ad_pq_genbus[ii],
                    [1, self._i, self._i, self._i],
                    [self._f, self._f, self._f, self._f, self._f, self._f, self._f],
                    self._s,
                )

            solved_flag = self.ifsolved(self.psse, 1, 3)

            if solved_flag == 0:
                n_ct_pq = n_ct_pq + n_step
                n_cur = n_cur + n_step
                self.psse.rawd_2(0, 1, [1, 1, 1, 0, 0, 0, 0], 0, step3_tempcase)
            else:
                if n_step >= 1:
                    if n_step == 2:
                        n_step = 1
                    else:
                        n_step = int(n_step / 4)
                else:
                    break
        return n_ct_pv, n_ct_pq, idx

    def sol_out_orig(self, solved_flag):
        if solved_flag == 0:
            logger.info("Orig PF converged at target loading. (Success!)\n")
        else:
            logger.info("Orig PF cannot converge at target loading.")

    def get_bus_list(self):
        bus_list = []
        for bus in self.raw_data.buses:
            ierr, kv = self.psse.busdat(bus, "KV")
            assert ierr == 0, f"error={ierr}"
            if kv > self.min_kv_filter and random.random() < self.filter_buses:
                bus_list.append(bus)

        return bus_list

    def get_added_generators(self, pfdt, ad_pq_busid, ad_pv_busid):
        ad_pq_genbus = []
        ad_pq_gen_q = []
        ad_pq_gen_q_abs = []

        ad_pv_genbus = []
        ad_pv_gen_q = []

        for ii in range(len(pfdt.gen_bus)):
            if pfdt.gen_id[ii] == "AD":
                if pfdt.gen_bus[ii] in ad_pq_busid:
                    ad_pq_genbus.append(pfdt.gen_bus[ii])
                    ad_pq_gen_q.append(pfdt.gen_Mvar[ii])
                    ad_pq_gen_q_abs.append(abs(pfdt.gen_Mvar[ii]))
                if pfdt.gen_bus[ii] in ad_pv_busid:
                    ad_pv_genbus.append(pfdt.gen_bus[ii])
                    ad_pv_gen_q.append(pfdt.gen_Mvar[ii])
        return ad_pq_genbus, ad_pq_gen_q, ad_pq_gen_q_abs, ad_pv_genbus, ad_pv_gen_q

    def get_q_of_added_generator(self, step3_tempcase, ad_pq_busid, ad_pv_busid):
        self.psse.read(0, step3_tempcase)
        self.psse.fnsl([0, 0, 0, 1, 1, 0, -1, 0])
        temp_genid = self.psse.amachchar(-1, 4, "ID")[1][0]
        temp_genbus = self.psse.amachint(-1, 4, "NUMBER")[1][0]
        temp_genoutput = np.asarray(self.psse.amachcplx(-1, 4, "PQGEN")[1][0])
        # temp_gen_mw = temp_genoutput.real
        temp_gen_mvar = temp_genoutput.imag

        ad_genbus = []
        ad_gen_q = []
        for ii in range(len(temp_genbus)):
            if temp_genid[ii] == "AD":
                if temp_genbus[ii] in ad_pq_busid:
                    ad_genbus.append(temp_genbus[ii])
                    ad_gen_q.append(temp_gen_mvar[ii])
                if temp_genbus[ii] in ad_pv_busid:
                    ad_genbus.append(temp_genbus[ii])
                    ad_gen_q.append(temp_gen_mvar[ii])
        return ad_genbus, ad_gen_q

    # By adjusting V set point at PV bus, those with close-to-zero
    # qinj can be removed directly (due to a better initial condition for NR)
    def remove_geni_adj_vj(self, ad_genbus, ad_gen_q, step4_tempcase, delta_thrd=1000):
        bus_remote = []
        q_remote = []
        v_set_remote = []
        for busi, q_i in zip(ad_genbus, ad_gen_q):
            q = []
            self.psse.read(0, step4_tempcase)
            self.psse.plant_chng_4(busi, 0, [self._i, self._i], [1.00, self._f])
            flag = self.ifsolved(self.psse, 1, 5)
            self.pfdt.getdata(self.psse)
            idxi = self.pfdt.gen_bus.index(busi)
            while self.pfdt.gen_id[idxi] != "AD":
                idxi = idxi + 1
            q.append(self.pfdt.gen_Mvar[idxi])

            self.psse.read(0, step4_tempcase)
            self.psse.plant_chng_4(busi, 0, [self._i, self._i], [0.99, self._f])
            flag = self.ifsolved(self.psse, 1, 5)
            self.pfdt.getdata(self.psse)
            idxi = self.pfdt.gen_bus.index(busi)
            while self.pfdt.gen_id[idxi] != "AD":
                idxi = idxi + 1
            q.append(self.pfdt.gen_Mvar[idxi])

            self.psse.read(0, step4_tempcase)
            self.psse.plant_chng_4(busi, 0, [self._i, self._i], [1.01, self._f])
            flag = self.ifsolved(self.psse, 1, 5)
            self.pfdt.getdata(self.psse)
            idxi = self.pfdt.gen_bus.index(busi)
            while self.pfdt.gen_id[idxi] != "AD":
                idxi = idxi + 1
            q.append(self.pfdt.gen_Mvar[idxi])

            a = (-1.0000 * q[0] + 0.5000 * q[1] + 0.5000 * q[2]) * 10000
            b = (2.0000 * q[0] - 1.0050 * q[1] - 0.9950 * q[2]) * 10000
            c = (-0.9999 * q[0] + 0.5050 * q[1] + 0.4950 * q[2]) * 10000

            delta = b * b - 4 * a * c

            if delta > delta_thrd:
                x1 = (-b + np.sqrt(b * b - 4 * a * c)) / 2 / a
                x2 = (-b - np.sqrt(b * b - 4 * a * c)) / 2 / a
                if abs(x1 - 1) < abs(x2 - 1):
                    vset = x1
                else:
                    vset = x2
                self.psse.read(0, step4_tempcase)
                self.psse.plant_chng_4(busi, 0, [self._i, self._i], [vset, self._f])
                self.psse.fnsl([0, 0, 0, 1, 1, 0, 0, 0])
                flag = self.ifsolved(self.psse, 1, 5)

                self.psse.purgmac(busi, r"""ad""")
                self.psse.bus_chng_3(
                    busi,
                    [1, self._i, self._i, self._i],
                    [self._f, self._f, self._f, self._f, self._f, self._f, self._f],
                    self._s,
                )
                flag = self.ifsolved(self.psse, 1, 3)
            else:
                flag = 2

            if flag == 0:
                pass
                # step4_tempcase = saveRaw(self.psse, rawfile, 5)
            else:
                logger.info("cannot remove gen" + str(busi))
                self.psse.read(0, step4_tempcase)

                self.pfdt.getdata(self.psse)
                idxi = self.pfdt.gen_bus.index(busi)
                while self.pfdt.gen_id[idxi] != "AD":
                    idxi = idxi + 1
                q_v_set = self.pfdt.gen_Mvar[idxi]

                bus_remote.append(busi)
                q_remote.append(q_v_set)
                v_set_remote.append(vset)
        return q_remote, bus_remote, v_set_remote

    # get nearby buses - single layer
    def get_near_by_bus(self, busi):
        nearbus = []
        nearpv = []
        last_found = -1
        while busi in self.pfdt.brc_from[last_found + 1 :]:
            last_found = self.pfdt.brc_from.index(busi, last_found + 1)
            if last_found == -1:
                break
            else:
                if (self.pfdt.brc_to[last_found] not in nearbus) & (self.pfdt.brc_to[last_found] != busi):
                    nearbus.append(self.pfdt.brc_to[last_found])
                    idx = self.pfdt.bus_num.index(self.pfdt.brc_to[last_found])
                    if self.pfdt.bus_type[idx] == 2:
                        nearpv.append(self.pfdt.brc_to[last_found])
        return nearbus, nearpv

    # get nearby pv buses
    def get_near_pv(self, busi, n_layer=1):
        # get nearby buses and nearby pv buses
        n = 1
        nearbus, nearpv = self.get_near_by_bus(busi)

        if len(nearpv) == 0:
            n_layer = n_layer + 1

        while n < n_layer:
            n = n + 1
            nearbus_pre = []
            for busii in nearbus:
                nearbus_pre.append(busii)

            for busii in nearbus_pre:
                nearbus_temp, nearpv_temp = self.get_near_by_bus(busii)
                for ii in range(len(nearbus_temp)):
                    if (nearbus_temp[ii] not in nearbus) & (nearbus_temp[ii] != busi):
                        nearbus.append(nearbus_temp[ii])
                for ii in range(len(nearpv_temp)):
                    if (nearpv_temp[ii] not in nearpv) & (nearpv_temp[ii] != busi):
                        nearpv.append(nearpv_temp[ii])
            if len(nearpv) == 0:
                n_layer = n_layer + 1

        return nearpv, n_layer

    def remove_geni_adj_vj(self, busi, busj, pfdt, step5_tempcase, vseti):
        q = []
        self.psse.read(0, step5_tempcase)
        self.psse.plant_chng_4(busi, 0, [self._i, self._i], [vseti, self._f])
        self.psse.plant_chng_4(busj, 0, [self._i, self._i], [1.0, self._f])
        flag = self.ifsolved(self.psse, 1, 5)
        pfdt.getdata(self.psse)
        idxi = pfdt.gen_bus.index(busi)
        while pfdt.gen_id[idxi] != "AD":
            idxi = idxi + 1
        q.append(pfdt.gen_Mvar[idxi])

        self.psse.read(0, step5_tempcase)
        self.psse.plant_chng_4(busi, 0, [self._i, self._i], [vseti, self._f])
        self.psse.plant_chng_4(busj, 0, [self._i, self._i], [1.01, self._f])
        flag = self.ifsolved(self.psse, 1, 5)
        pfdt.getdata(self.psse)
        idxi = pfdt.gen_bus.index(busi)
        while pfdt.gen_id[idxi] != "AD":
            idxi = idxi + 1
        q.append(pfdt.gen_Mvar[idxi])

        a = (-1.0000 * q[0] + 1.0000 * q[1]) * 100
        b = q[0] - a
        if a != 0:
            vset = -b / a + 0.01

            self.psse.read(0, step5_tempcase)
            self.psse.plant_chng_4(busi, 0, [self._i, self._i], [vseti, self._f])
            self.psse.plant_chng_4(busj, 0, [self._i, self._i], [vset, self._f])
            self.psse.fnsl([0, 0, 0, 1, 1, 0, 0, 0])
            flag = self.ifsolved(self.psse, 1, 5)

            self.psse.purgmac(busi, r"""ad""")
            self.psse.bus_chng_3(
                busi,
                [1, self._i, self._i, self._i],
                [self._f, self._f, self._f, self._f, self._f, self._f, self._f],
                self._s,
            )
            flag = self.ifsolved(self.psse, 1, 3)
        else:
            vset = 0
            flag = 2

        return vset, flag

    def remove_geni_adj_vi(self, ad_genbus, ad_gen_q, step4_tempcase, delta_thrd=1000):
        bus_remote = []
        q_remote = []
        v_set_remote = []
        for busi, q_i in zip(ad_genbus, ad_gen_q):
            q = []
            self.psse.read(0, step4_tempcase)
            self.psse.plant_chng_4(busi, 0, [self._i, self._i], [1.00, self._f])
            flag = self.if_solved(1, 5)
            self.pfdt.getdata(self.psse)
            idxi = self.pfdt.gen_bus.index(busi)
            while self.pfdt.gen_id[idxi] != "AD":
                idxi = idxi + 1
            q.append(self.pfdt.gen_Mvar[idxi])

            self.psse.read(0, step4_tempcase)
            self.psse.plant_chng_4(busi, 0, [self._i, self._i], [0.99, self._f])
            flag = self.if_solved(1, 5)
            self.pfdt.getdata(self.psse)
            idxi = self.pfdt.gen_bus.index(busi)
            while self.pfdt.gen_id[idxi] != "AD":
                idxi = idxi + 1
            q.append(self.pfdt.gen_Mvar[idxi])

            self.psse.read(0, step4_tempcase)
            self.psse.plant_chng_4(busi, 0, [self._i, self._i], [1.01, self._f])
            flag = self.if_solved(1, 5)
            self.pfdt.getdata(self.psse)
            idxi = self.pfdt.gen_bus.index(busi)
            while self.pfdt.gen_id[idxi] != "AD":
                idxi = idxi + 1
            q.append(self.pfdt.gen_Mvar[idxi])

            a = (-1.0000 * q[0] + 0.5000 * q[1] + 0.5000 * q[2]) * 10000
            b = (2.0000 * q[0] - 1.0050 * q[1] - 0.9950 * q[2]) * 10000
            c = (-0.9999 * q[0] + 0.5050 * q[1] + 0.4950 * q[2]) * 10000

            delta = b * b - 4 * a * c

            if delta > delta_thrd:
                x1 = (-b + np.sqrt(b * b - 4 * a * c)) / 2 / a
                x2 = (-b - np.sqrt(b * b - 4 * a * c)) / 2 / a
                if abs(x1 - 1) < abs(x2 - 1):
                    vset = x1
                else:
                    vset = x2
                self.psse.read(0, step4_tempcase)
                self.psse.plant_chng_4(busi, 0, [self._i, self._i], [vset, self._f])
                self.psse.fnsl([0, 0, 0, 1, 1, 0, 0, 0])
                flag = self.if_solved(1, 5)

                self.psse.purgmac(busi, r"""ad""")
                self.psse.bus_chng_3(
                    busi,
                    [1, self._i, self._i, self._i],
                    [self._f, self._f, self._f, self._f, self._f, self._f, self._f],
                    self._s,
                )
                flag = self.if_solved(1, 3)
            else:
                flag = 2

            if flag == 0:
                pass
                # step4_tempcase = self.save_raw(self.psse, rawfile, 5)
            else:
                logger.info("cannot remove gen" + str(busi))
                self.psse.read(0, step4_tempcase)

                self.pfdt.getdata(self.psse)
                idxi = self.pfdt.gen_bus.index(busi)
                while self.pfdt.gen_id[idxi] != "AD":
                    idxi = idxi + 1
                q_v_set = self.pfdt.gen_Mvar[idxi]

                bus_remote.append(busi)
                q_remote.append(q_v_set)
                v_set_remote.append(vset)
        return q_remote, bus_remote, v_set_remote
