# OPA-NL-021 — Independent frozen Margin16 robustness confirmation at 42 ps

Status: proposed preregistration; no NL021 test inputs generated or experiment run. This is a new baseline confirmation study, not advancement of any NL020 robust candidate. NL020 had no qualifying robust candidate; its endpoint and rules remain unchanged.

## NL020 raw evidence audit

Source run 44492281387, archive merge 54b50174912c9d76583371368a201f5db18f880e, provenance SHA-256 db3f4d1fd013999510ad0ac4386641f88919de33ceb9b612c69e264205a04980. Independent CSV inspection verified 200 primary rows, 600 resolution rows, 40 primary groups, 120 resolution groups, 20 tuples, 12 coefficient links, 5440 paired rows and 136 summaries; exact key coverage, both marginals, repeat minima, grid and group gates, frozen NL019 vector identity and normalized variance. All 180 risk cells checked against their recorded log-sum-exp weights and final objective. New reproducible research/analyze_nl020.py additionally checks byte hashes, vector digests, optimizer and base-weight identities; must execute before NL021 test generation. Script not yet executed.

Low-drive worst-repeat counts (denominator 2048):

| LO | seed | frozen Ridge | frozen Margin | fresh Ridge | fresh Margin | Softmax | Repeat |
|---:|---:|---:|---:|---:|---:|---:|---:|
|2|1301|1969|1986|1969|1985|1988|1987|
|2|1302|2001|2001|2001|2001|2001|2000|
|2|1303|1959|1973|1959|1973|1972|1972|
|2|1304|1956|1975|1956|1976|1975|1974|
|2|1305|1991|2000|1991|1999|1999|1998|
|3|1301|1970|1987|1969|1988|1988|1988|
|3|1302|2003|2004|2002|2002|2003|2002|
|3|1303|1960|1974|1961|1973|1972|1972|
|3|1304|1958|1979|1959|1977|1979|1981|
|3|1305|1991|2000|1992|2001|1999|2000|

Matched low-drive net vs fresh margin by seed 1301..1305: LO2 softmax [5,-1,-2,3,-1], repeat [7,-1,-1,0,-1]; LO3 softmax [1,3,0,11,-3], repeat [1,2,-1,15,-3]. No robust method improves seed1303 worst; all lose one decision. Risk aggregation works numerically but direction changes are small.

| LO | method | cosine vs fresh margin | previous-symbol relative norm | low-drive effective weight | seed1303 low effective weight |
|---:|---|---:|---:|---:|---:|
|2|fresh margin|1|.21718560948968857|.8|.16|
|2|frozen margin|.9971623203499795|.2288603969493172|.8|.16|
|2|softmax|.9999009006881866|.22073563880824942|.9362281443294238|.23962015019195296|
|2|repeat|.9998230877903405|.21969869691873006|.93770085335282|.24337722777591553|
|3|fresh margin|1|.21869652023365357|.8|.16|
|3|frozen margin|.9972112629106934|.2304133172255779|.8|.16|
|3|softmax|.9999018727456213|.22222126767079056|.9343655353713864|.23872509416377688|
|3|repeat|.9998240533635288|.2213002369912258|.9358153924547151|.2424118414603204|

Softmax low-drive seed weights LO2 [.1822969398632465,.14670937842341988,.23962015019195296,.20100433073152207,.16659734511928234], LO3 [.1818728674481803,.14707537763012504,.23872509416377688,.19987567189439095,.16681652423491333]. Repeat largest individual cell is seed1303 calibration repeat4 at both settings (.04131851949267642/.040862934468035746 vs base .02); limiting test repeat1 is not the same draw. Robust optimizer gradients 5.2361296505685356e-8..4.5820293977524254e-7, 33..36 iterations. All clean minima 1. At LO3 electrical-only worst fresh margin .97265625, frozen margin .97216796875, softmax .97265625, repeat .97314453125; mean normalized noise amplification .44502578846596064,.44480289124834843,.4444911904244363,.44416166755386505 respectively. Small changes in electrical noise do not yield robust maximin improvement. No proof of a fundamental 16-tap ceiling. No tau sweep using old test data.

## Fixed hypothesis and endpoints

Test whether the exact archived NL019 Margin16 Low receiver independently attains combined worst >=.96 on **both new panels and both drives**, with all existing quality/physics gates. Primary endpoint: C2, 42 ps, zero gap, 5 ps response, LO3 mW, 120 GHz, frozen_margin16_low (NL019 vector). Chosen before new data because best NL020 maximin; secondary lower-LO endpoint same readout at LO2 mW. NL019 missed .96 (LO3 .9599609375); NL020 reached .9638671875 on one new panel. Neither is independent two-panel confirmation. No retroactive advancement. Fixed settings LO2/3, same archived five absorber weights, same receiver physics/PSD, causal 16 taps, no intercept, fixed zero sign threshold. No new fitting whatsoever. Compare exactly nine readouts per setting: four anchors end,eighth_mean,quarter_mean,half_mean; frozen_fresh_ridge16, frozen_margin16_low, frozen_nl020_margin16_low, frozen_nl020_robust16_softmax, frozen_nl020_robust16_repeat. All five coefficient readouts frozen. First two records copied from NL020 frozen records, verified against NL019; remaining three from NL020 fit records. Supportive comparisons cannot rescue primary failure.

| LO mW | archived NL020 readout | SHA-256 |
|---:|---|---|
| 2 | frozen_fresh_ridge16 | 14ece62bd1ae78e44a5e3dafdad65812ea842176cab03e0447985a8222026f2e |
| 2 | frozen_margin16_low | 18cf11e4e6c904ae8e1e04449c1bf9f90f0b99c43826116a869dc5f92f65f6d4 |
| 2 | margin16_low | d27d6db4bfda06590085962c3713732ee75c26e53bd10e2e98f28a9e9d7cb652 |
| 2 | robust16_softmax | 4ac2a105529dcc571cabd256fab295c3f5732c140f701178fd5f259f9c72487b |
| 2 | robust16_repeat | 600c469daea67315f208ba39d49fa8757f84fb5e4eb7332d61956ab1e56fda4e |
| 3 | frozen_fresh_ridge16 | 658ad54e42916effde948d7e0141e4517c64906c4c705033ac47bd914d9626eb |
| 3 | frozen_margin16_low | 0e7e248644f97810db177da4dabc09b6ef7f581bfb46129d85457df45d23e0ef |
| 3 | margin16_low | ac6504228d6f25ca59b4621ee347cf57038c140a98619c568fbc5b2533382712 |
| 3 | robust16_softmax | 676efedf8772610f17988a68d09f40681d0335bc268139108df1d3f16f128a86 |
| 3 | robust16_repeat | 7311b9000318371577bd03a077915e5542002baace65c11603113d25b5094d18 |

## Independent panels and gates

Panel A domains 10904..10908; panel B 10914..10918; disjoint from each other and all prior calibration/test domains. Same five seeds 1301..1305 and drives .1/1 mW, 2048 balanced examples per seed/drive per panel (8 streams x256), eight independent noise repeats, same paired underlying draws within panel across settings, readouts and aligned grids. Independent draws across panels, same model instances (not generalization to new model weights). Preserve all startup symbols. Verify exact frozen hashes and archived bytes, run research/analyze_nl020.py before any test generation. Three grids finest .0625 ps, unchanged tolerances, inherited 95% unfiltered/clean/combined gates, stationary eligibility and sampled diode cap 2 mW; unchanged middle/fine electrical and combined gate agreement. Explicitly also require middle/fine agreement on .96 combined group threshold for confirmation (report any ambiguity; no upgrading). Primary succeeds only if all four panel/drive groups pass inherited gates and exact combined worst >=.96 at middle and fine. Worst-repeat count >=1967/2048. Secondary same separate criterion; no substitute primary, no post-hoc selection or rerun-until-pass. If primary fails, report failure even if secondary or another reference passes. If primary passes, independent simulation confirmation at 23.81 Gsymbol/s under these specified panels only; report 95% and 96% gates separately. No speed promotion. If secondary also passes, report lower LO as supportive, not a replacement endpoint.

## Counts and pairing

2 panels x2 settings x9 methods x2 drives x5 seeds =360 primary rows,1080 resolution rows,72 primary groups,216 resolution groups,18 common two-panel tuples,10 frozen coefficient records,6 optical audits,4 convergence comparisons. Pair all five coefficient readouts against four anchors (20 pairs/setting); frozen_margin16_low vs frozen_fresh_ridge16; frozen_nl020_margin16_low vs frozen_margin16_low and frozen_fresh_ridge16; both robust references vs frozen_nl020_margin16_low, frozen_margin16_low and frozen_fresh_ridge16; repeat vs softmax. Total 30 pairs/setting x2 panels x2 settings x2 drives x5 seeds x8 repeats=9600 paired raw rows,240 summaries each 81920 decisions. Exact key coverage, both marginals, all seed and repeat counts, normalized noise and coefficient directions, optical energy balance, immutable archive and vector file, all numerical checks. Report every endpoint and all four primary/secondary group outcomes; no independent-trial significance claim. No fitting, no optimization of temperature, no adaptive selection. No measured BER, total wall-plug power, physical throughput or ADC feasibility claim. Only after confirmation and archive audit consider a separately preregistered 41 ps exploration; 40 ps remains long-term goal. If primary fails, reconsider robustness or longer periods, not threshold relaxation.
