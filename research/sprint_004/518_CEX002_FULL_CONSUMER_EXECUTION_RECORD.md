# CEX-002 Record 518 — Full consumer execution

Launch UTC: 2026-10-21T05:01:23Z
Execution HEAD: 2e7fadb34e2a434c44da6502c617c97490f04f47

## Raw checker output

```jsonl
{"candidate_sha256":"8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34","completed_files":0,"completed_rows":0,"elapsed_seconds":40.229,"stage":"authenticated_descriptor"}
{"completed_files":1024,"completed_rows":252,"elapsed_seconds":41.846,"stage":"roundtrip"}
{"completed_files":2048,"completed_rows":771,"elapsed_seconds":44.437,"stage":"roundtrip"}
{"completed_files":3072,"completed_rows":771,"elapsed_seconds":44.894,"stage":"roundtrip"}
{"completed_files":4096,"completed_rows":771,"elapsed_seconds":45.338,"stage":"roundtrip"}
{"completed_files":5120,"completed_rows":771,"elapsed_seconds":45.784,"stage":"roundtrip"}
{"completed_files":6144,"completed_rows":771,"elapsed_seconds":46.226,"stage":"roundtrip"}
{"completed_files":7168,"completed_rows":771,"elapsed_seconds":46.672,"stage":"roundtrip"}
{"completed_files":8192,"completed_rows":771,"elapsed_seconds":47.107,"stage":"roundtrip"}
{"completed_files":9216,"completed_rows":771,"elapsed_seconds":47.554,"stage":"roundtrip"}
{"completed_files":10240,"completed_rows":771,"elapsed_seconds":47.999,"stage":"roundtrip"}
{"completed_files":11264,"completed_rows":771,"elapsed_seconds":48.438,"stage":"roundtrip"}
{"completed_files":12288,"completed_rows":771,"elapsed_seconds":48.895,"stage":"roundtrip"}
{"completed_files":13312,"completed_rows":771,"elapsed_seconds":49.343,"stage":"roundtrip"}
{"completed_files":14336,"completed_rows":771,"elapsed_seconds":49.817,"stage":"roundtrip"}
{"completed_files":15360,"completed_rows":771,"elapsed_seconds":50.282,"stage":"roundtrip"}
{"completed_files":16384,"completed_rows":771,"elapsed_seconds":50.72,"stage":"roundtrip"}
{"completed_files":17408,"completed_rows":771,"elapsed_seconds":51.16,"stage":"roundtrip"}
{"completed_files":18432,"completed_rows":771,"elapsed_seconds":51.618,"stage":"roundtrip"}
{"completed_files":19456,"completed_rows":771,"elapsed_seconds":52.066,"stage":"roundtrip"}
{"completed_files":20480,"completed_rows":771,"elapsed_seconds":52.506,"stage":"roundtrip"}
{"completed_files":21504,"completed_rows":771,"elapsed_seconds":52.958,"stage":"roundtrip"}
{"completed_files":22528,"completed_rows":771,"elapsed_seconds":53.404,"stage":"roundtrip"}
{"completed_files":23552,"completed_rows":771,"elapsed_seconds":53.853,"stage":"roundtrip"}
{"completed_files":24576,"completed_rows":283250,"elapsed_seconds":126.044,"stage":"roundtrip"}
{"completed_files":25600,"completed_rows":1005699,"elapsed_seconds":300.869,"stage":"roundtrip"}
{"completed_files":26624,"completed_rows":1730892,"elapsed_seconds":478.945,"stage":"roundtrip"}
{"completed_files":27648,"completed_rows":2459355,"elapsed_seconds":666.38,"stage":"roundtrip"}
{"completed_files":28672,"completed_rows":3184194,"elapsed_seconds":868.708,"stage":"roundtrip"}
{"completed_files":29696,"completed_rows":3906899,"elapsed_seconds":1051.447,"stage":"roundtrip"}
{"completed_files":30720,"completed_rows":4634522,"elapsed_seconds":1255.633,"stage":"roundtrip"}
{"completed_files":31744,"completed_rows":5360683,"elapsed_seconds":1418.548,"stage":"roundtrip"}
{"completed_files":32768,"completed_rows":6086024,"elapsed_seconds":1580.704,"stage":"roundtrip"}
{"completed_files":33792,"completed_rows":6809860,"elapsed_seconds":1742.47,"stage":"roundtrip"}
{"completed_files":34816,"completed_rows":7533843,"elapsed_seconds":1919.996,"stage":"roundtrip"}
{"completed_files":35840,"completed_rows":8258816,"elapsed_seconds":2084.524,"stage":"roundtrip"}
{"completed_files":36864,"completed_rows":8987044,"elapsed_seconds":2250.589,"stage":"roundtrip"}
{"completed_files":37888,"completed_rows":9708351,"elapsed_seconds":2415.421,"stage":"roundtrip"}
{"completed_files":38912,"completed_rows":10434021,"elapsed_seconds":2581.788,"stage":"roundtrip"}
{"completed_files":39936,"completed_rows":11157042,"elapsed_seconds":2761.363,"stage":"roundtrip"}
{"completed_files":40960,"completed_rows":11882356,"elapsed_seconds":2923.997,"stage":"roundtrip"}
{"completed_files":41984,"completed_rows":12608443,"elapsed_seconds":3092.621,"stage":"roundtrip"}
{"completed_files":43008,"completed_rows":13335281,"elapsed_seconds":3261.381,"stage":"roundtrip"}
{"completed_files":44032,"completed_rows":14062263,"elapsed_seconds":3437.916,"stage":"roundtrip"}
{"completed_files":45056,"completed_rows":14786375,"elapsed_seconds":3606.556,"stage":"roundtrip"}
{"completed_files":46080,"completed_rows":15515723,"elapsed_seconds":3783.571,"stage":"roundtrip"}
{"completed_files":47104,"completed_rows":16034394,"elapsed_seconds":3900.725,"stage":"roundtrip"}
{"completed_files":48128,"completed_rows":16034394,"elapsed_seconds":3901.176,"stage":"roundtrip"}
{"completed_files":49152,"completed_rows":16034394,"elapsed_seconds":3901.621,"stage":"roundtrip"}
{"completed_files":50176,"completed_rows":16034394,"elapsed_seconds":3902.074,"stage":"roundtrip"}
{"completed_files":51200,"completed_rows":16034394,"elapsed_seconds":3902.52,"stage":"roundtrip"}
{"completed_files":52224,"completed_rows":16034394,"elapsed_seconds":3902.983,"stage":"roundtrip"}
{"completed_files":53248,"completed_rows":16034394,"elapsed_seconds":3903.424,"stage":"roundtrip"}
{"completed_files":54272,"completed_rows":16034394,"elapsed_seconds":3903.88,"stage":"roundtrip"}
{"completed_files":55296,"completed_rows":16034394,"elapsed_seconds":3904.327,"stage":"roundtrip"}
{"completed_files":56320,"completed_rows":16034394,"elapsed_seconds":3904.781,"stage":"roundtrip"}
{"completed_files":57344,"completed_rows":16034394,"elapsed_seconds":3905.24,"stage":"roundtrip"}
{"completed_files":58368,"completed_rows":16034394,"elapsed_seconds":3905.696,"stage":"roundtrip"}
{"completed_files":59392,"completed_rows":16034394,"elapsed_seconds":3906.171,"stage":"roundtrip"}
{"completed_files":60416,"completed_rows":16034394,"elapsed_seconds":3906.647,"stage":"roundtrip"}
{"completed_files":61440,"completed_rows":16034394,"elapsed_seconds":3907.113,"stage":"roundtrip"}
{"completed_files":62464,"completed_rows":16034394,"elapsed_seconds":3907.582,"stage":"roundtrip"}
{"completed_files":63488,"completed_rows":16034394,"elapsed_seconds":3908.028,"stage":"roundtrip"}
{"completed_files":64512,"completed_rows":16034394,"elapsed_seconds":3908.476,"stage":"roundtrip"}
{"completed_files":65536,"completed_rows":16034394,"elapsed_seconds":3908.942,"stage":"roundtrip"}
{"completed_files":66560,"completed_rows":16034394,"elapsed_seconds":3909.394,"stage":"roundtrip"}
{"completed_files":67584,"completed_rows":16034394,"elapsed_seconds":3909.878,"stage":"roundtrip"}
{"completed_files":68608,"completed_rows":16034394,"elapsed_seconds":3910.344,"stage":"roundtrip"}
{"completed_files":69632,"completed_rows":16164722,"elapsed_seconds":3937.946,"stage":"roundtrip"}
{"completed_files":70656,"completed_rows":16891661,"elapsed_seconds":4088.569,"stage":"roundtrip"}
{"completed_files":71680,"completed_rows":17613263,"elapsed_seconds":4234.94,"stage":"roundtrip"}
{"completed_files":72704,"completed_rows":18340336,"elapsed_seconds":4380.046,"stage":"roundtrip"}
{"completed_files":73728,"completed_rows":19065951,"elapsed_seconds":4521.084,"stage":"roundtrip"}
{"completed_files":74752,"completed_rows":19790588,"elapsed_seconds":4665.626,"stage":"roundtrip"}
{"completed_files":75776,"completed_rows":20517265,"elapsed_seconds":4806.938,"stage":"roundtrip"}
{"completed_files":76800,"completed_rows":21242936,"elapsed_seconds":4945.808,"stage":"roundtrip"}
{"completed_files":77824,"completed_rows":21970924,"elapsed_seconds":5085.643,"stage":"roundtrip"}
{"completed_files":78848,"completed_rows":22692154,"elapsed_seconds":5220.733,"stage":"roundtrip"}
{"completed_files":79872,"completed_rows":23414603,"elapsed_seconds":5358.338,"stage":"roundtrip"}
{"completed_files":80896,"completed_rows":24142547,"elapsed_seconds":5500.334,"stage":"roundtrip"}
{"completed_files":81920,"completed_rows":24868117,"elapsed_seconds":5637.987,"stage":"roundtrip"}
{"completed_files":82944,"completed_rows":25591566,"elapsed_seconds":5780.055,"stage":"roundtrip"}
{"completed_files":83968,"completed_rows":26316044,"elapsed_seconds":5920.241,"stage":"roundtrip"}
{"completed_files":84992,"completed_rows":27042717,"elapsed_seconds":6065.008,"stage":"roundtrip"}
{"completed_files":86016,"completed_rows":27765562,"elapsed_seconds":6205.918,"stage":"roundtrip"}
{"completed_files":87040,"completed_rows":28491161,"elapsed_seconds":6343.911,"stage":"roundtrip"}
{"completed_files":88064,"completed_rows":29216961,"elapsed_seconds":6477.894,"stage":"roundtrip"}
{"completed_files":89088,"completed_rows":29944010,"elapsed_seconds":6618.97,"stage":"roundtrip"}
{"completed_files":90112,"completed_rows":30670608,"elapsed_seconds":6754.776,"stage":"roundtrip"}
{"completed_files":91136,"completed_rows":31395349,"elapsed_seconds":6887.021,"stage":"roundtrip"}
{"completed_files":92160,"completed_rows":32068017,"elapsed_seconds":7013.509,"stage":"roundtrip"}
{"completed_files":93184,"completed_rows":32068017,"elapsed_seconds":7014.128,"stage":"roundtrip"}
{"completed_files":94208,"completed_rows":32068017,"elapsed_seconds":7014.718,"stage":"roundtrip"}
{"completed_files":95232,"completed_rows":32068017,"elapsed_seconds":7015.327,"stage":"roundtrip"}
{"completed_files":96256,"completed_rows":32068017,"elapsed_seconds":7015.927,"stage":"roundtrip"}
{"completed_files":97280,"completed_rows":32068017,"elapsed_seconds":7016.583,"stage":"roundtrip"}
{"completed_files":98304,"completed_rows":32068017,"elapsed_seconds":7017.172,"stage":"roundtrip"}
{"completed_files":99328,"completed_rows":32068017,"elapsed_seconds":7017.757,"stage":"roundtrip"}
{"completed_files":100352,"completed_rows":32068017,"elapsed_seconds":7018.35,"stage":"roundtrip"}
{"completed_files":101376,"completed_rows":32068017,"elapsed_seconds":7018.951,"stage":"roundtrip"}
{"completed_files":102400,"completed_rows":32068017,"elapsed_seconds":7019.546,"stage":"roundtrip"}
{"completed_files":103424,"completed_rows":32068017,"elapsed_seconds":7020.157,"stage":"roundtrip"}
{"completed_files":104448,"completed_rows":32068017,"elapsed_seconds":7020.755,"stage":"roundtrip"}
{"completed_files":105472,"completed_rows":32068017,"elapsed_seconds":7021.342,"stage":"roundtrip"}
{"completed_files":106496,"completed_rows":32068017,"elapsed_seconds":7021.93,"stage":"roundtrip"}
{"completed_files":107520,"completed_rows":32068017,"elapsed_seconds":7022.52,"stage":"roundtrip"}
{"completed_files":108544,"completed_rows":32068017,"elapsed_seconds":7023.116,"stage":"roundtrip"}
{"completed_files":109568,"completed_rows":32068017,"elapsed_seconds":7023.716,"stage":"roundtrip"}
{"completed_files":110592,"completed_rows":32068017,"elapsed_seconds":7024.326,"stage":"roundtrip"}
{"completed_files":111616,"completed_rows":32068017,"elapsed_seconds":7024.933,"stage":"roundtrip"}
{"completed_files":112640,"completed_rows":38719986,"elapsed_seconds":8367.178,"stage":"roundtrip"}
{"completed_files":113664,"completed_rows":46691410,"elapsed_seconds":9959.255,"stage":"roundtrip"}
{"completed_files":114688,"completed_rows":55296014,"elapsed_seconds":11684.732,"stage":"roundtrip"}
{"completed_files":115712,"completed_rows":63813910,"elapsed_seconds":13390.119,"stage":"roundtrip"}
{"completed_files":116736,"completed_rows":72017575,"elapsed_seconds":15031.579,"stage":"roundtrip"}
{"completed_files":117760,"completed_rows":80219127,"elapsed_seconds":16655.628,"stage":"roundtrip"}
{"completed_files":118784,"completed_rows":88572913,"elapsed_seconds":18302.427,"stage":"roundtrip"}
{"completed_files":119808,"completed_rows":96725710,"elapsed_seconds":19907.752,"stage":"roundtrip"}
{"completed_files":120832,"completed_rows":104995718,"elapsed_seconds":21554.59,"stage":"roundtrip"}
{"completed_files":121856,"completed_rows":113540280,"elapsed_seconds":23246.681,"stage":"roundtrip"}
{"completed_files":122880,"completed_rows":121770929,"elapsed_seconds":24909.188,"stage":"roundtrip"}
{"completed_files":123904,"completed_rows":129860637,"elapsed_seconds":26535.084,"stage":"roundtrip"}
{"completed_files":124928,"completed_rows":137900823,"elapsed_seconds":28192.593,"stage":"roundtrip"}
{"completed_files":125952,"completed_rows":146245743,"elapsed_seconds":29936.659,"stage":"roundtrip"}
{"completed_files":126976,"completed_rows":154533402,"elapsed_seconds":31661.364,"stage":"roundtrip"}
{"completed_files":128000,"completed_rows":162795279,"elapsed_seconds":33399.863,"stage":"roundtrip"}
{"completed_files":129024,"completed_rows":171269159,"elapsed_seconds":35120.291,"stage":"roundtrip"}
{"completed_files":130048,"completed_rows":179624914,"elapsed_seconds":36820.269,"stage":"roundtrip"}
{"completed_files":131072,"completed_rows":188062348,"elapsed_seconds":38542.992,"stage":"roundtrip"}
{"completed_files":132096,"completed_rows":192273963,"elapsed_seconds":39449.534,"stage":"roundtrip"}
{"completed_files":133120,"completed_rows":192273963,"elapsed_seconds":39450.078,"stage":"roundtrip"}
{"completed_files":134144,"completed_rows":192273963,"elapsed_seconds":39450.609,"stage":"roundtrip"}
{"completed_files":135168,"completed_rows":192273963,"elapsed_seconds":39451.146,"stage":"roundtrip"}
{"completed_files":136192,"completed_rows":192273963,"elapsed_seconds":39451.674,"stage":"roundtrip"}
{"completed_files":137216,"completed_rows":192273963,"elapsed_seconds":39452.205,"stage":"roundtrip"}
{"completed_files":138240,"completed_rows":192273963,"elapsed_seconds":39452.73,"stage":"roundtrip"}
{"completed_files":139264,"completed_rows":192273963,"elapsed_seconds":39453.251,"stage":"roundtrip"}
{"completed_files":140288,"completed_rows":192273963,"elapsed_seconds":39453.775,"stage":"roundtrip"}
{"completed_files":141312,"completed_rows":192273963,"elapsed_seconds":39454.302,"stage":"roundtrip"}
{"completed_files":142336,"completed_rows":192273963,"elapsed_seconds":39454.961,"stage":"roundtrip"}
{"completed_files":143360,"completed_rows":192273963,"elapsed_seconds":39455.493,"stage":"roundtrip"}
{"completed_files":144384,"completed_rows":192273963,"elapsed_seconds":39456.041,"stage":"roundtrip"}
{"completed_files":145408,"completed_rows":192273963,"elapsed_seconds":39456.577,"stage":"roundtrip"}
{"completed_files":146432,"completed_rows":192273963,"elapsed_seconds":39457.131,"stage":"roundtrip"}
{"completed_files":147456,"completed_rows":192273963,"elapsed_seconds":39457.841,"stage":"roundtrip"}
{"completed_files":148480,"completed_rows":192273963,"elapsed_seconds":39458.499,"stage":"roundtrip"}
{"completed_files":149504,"completed_rows":192273963,"elapsed_seconds":39459.264,"stage":"roundtrip"}
{"completed_files":150528,"completed_rows":192273963,"elapsed_seconds":39459.97,"stage":"roundtrip"}
{"completed_files":151552,"completed_rows":192273963,"elapsed_seconds":39460.665,"stage":"roundtrip"}
{"completed_files":152576,"completed_rows":192273963,"elapsed_seconds":39461.309,"stage":"roundtrip"}
{"completed_files":153600,"completed_rows":192399494,"elapsed_seconds":39483.795,"stage":"roundtrip"}
{"completed_files":154624,"completed_rows":192529551,"elapsed_seconds":39506.353,"stage":"roundtrip"}
{"completed_files":155648,"completed_rows":192650972,"elapsed_seconds":39528.971,"stage":"roundtrip"}
{"completed_files":156672,"completed_rows":192776663,"elapsed_seconds":39550.805,"stage":"roundtrip"}
{"completed_files":157696,"completed_rows":192901999,"elapsed_seconds":39576.44,"stage":"roundtrip"}
{"completed_files":158720,"completed_rows":193020948,"elapsed_seconds":39599.89,"stage":"roundtrip"}
{"completed_files":159744,"completed_rows":193140635,"elapsed_seconds":39624.012,"stage":"roundtrip"}
{"completed_files":160768,"completed_rows":193266061,"elapsed_seconds":39646.945,"stage":"roundtrip"}
{"completed_files":161792,"completed_rows":193390273,"elapsed_seconds":39669.705,"stage":"roundtrip"}
{"completed_files":162816,"completed_rows":193523905,"elapsed_seconds":39695.964,"stage":"roundtrip"}
{"completed_files":163840,"completed_rows":193658071,"elapsed_seconds":39720.092,"stage":"roundtrip"}
{"completed_files":164864,"completed_rows":193775178,"elapsed_seconds":39742.078,"stage":"roundtrip"}
{"completed_files":165888,"completed_rows":193917780,"elapsed_seconds":39767.11,"stage":"roundtrip"}
{"completed_files":166912,"completed_rows":194055802,"elapsed_seconds":39793.676,"stage":"roundtrip"}
{"completed_files":167936,"completed_rows":194207057,"elapsed_seconds":39820.12,"stage":"roundtrip"}
{"completed_files":168960,"completed_rows":194336471,"elapsed_seconds":39844.391,"stage":"roundtrip"}
{"completed_files":169984,"completed_rows":194469491,"elapsed_seconds":39868.349,"stage":"roundtrip"}
{"completed_files":171008,"completed_rows":194614391,"elapsed_seconds":39893.685,"stage":"roundtrip"}
{"completed_files":172032,"completed_rows":194761312,"elapsed_seconds":39919.237,"stage":"roundtrip"}
{"completed_files":173056,"completed_rows":194883161,"elapsed_seconds":39942.045,"stage":"roundtrip"}
{"completed_files":174080,"completed_rows":194956987,"elapsed_seconds":39955.815,"stage":"roundtrip"}
{"completed_files":175104,"completed_rows":194956987,"elapsed_seconds":39956.419,"stage":"roundtrip"}
{"completed_files":176128,"completed_rows":194956987,"elapsed_seconds":39957.009,"stage":"roundtrip"}
{"completed_files":177152,"completed_rows":194956987,"elapsed_seconds":39957.604,"stage":"roundtrip"}
{"completed_files":178176,"completed_rows":194956987,"elapsed_seconds":39958.203,"stage":"roundtrip"}
{"completed_files":179200,"completed_rows":194956987,"elapsed_seconds":39958.812,"stage":"roundtrip"}
{"completed_files":180224,"completed_rows":194956987,"elapsed_seconds":39959.405,"stage":"roundtrip"}
{"completed_files":181248,"completed_rows":194956987,"elapsed_seconds":39960.007,"stage":"roundtrip"}
{"completed_files":182272,"completed_rows":194956987,"elapsed_seconds":39960.64,"stage":"roundtrip"}
{"completed_files":183296,"completed_rows":194956987,"elapsed_seconds":39961.24,"stage":"roundtrip"}
{"completed_files":184320,"completed_rows":194956987,"elapsed_seconds":39961.846,"stage":"roundtrip"}
{"completed_files":185344,"completed_rows":194956987,"elapsed_seconds":39962.453,"stage":"roundtrip"}
{"completed_files":186368,"completed_rows":194956987,"elapsed_seconds":39963.053,"stage":"roundtrip"}
{"completed_files":187392,"completed_rows":194956987,"elapsed_seconds":39963.65,"stage":"roundtrip"}
{"completed_files":188416,"completed_rows":194956987,"elapsed_seconds":39964.243,"stage":"roundtrip"}
{"completed_files":189440,"completed_rows":194956987,"elapsed_seconds":39964.86,"stage":"roundtrip"}
{"completed_files":190464,"completed_rows":194956987,"elapsed_seconds":39965.467,"stage":"roundtrip"}
{"completed_files":191488,"completed_rows":194956987,"elapsed_seconds":39966.078,"stage":"roundtrip"}
{"completed_files":192512,"completed_rows":194956987,"elapsed_seconds":39966.676,"stage":"roundtrip"}
{"completed_files":193536,"completed_rows":194956987,"elapsed_seconds":39967.273,"stage":"roundtrip"}
{"completed_files":194560,"completed_rows":194956987,"elapsed_seconds":39967.872,"stage":"roundtrip"}
{"completed_files":195584,"completed_rows":195263091,"elapsed_seconds":40032.823,"stage":"roundtrip"}
{"completed_files":196608,"completed_rows":195981971,"elapsed_seconds":40178.247,"stage":"roundtrip"}
{"completed_files":197632,"completed_rows":196704638,"elapsed_seconds":40327.77,"stage":"roundtrip"}
{"completed_files":198656,"completed_rows":197428433,"elapsed_seconds":40482.79,"stage":"roundtrip"}
{"completed_files":199680,"completed_rows":198147428,"elapsed_seconds":40645.749,"stage":"roundtrip"}
{"completed_files":200704,"completed_rows":198863301,"elapsed_seconds":40800.26,"stage":"roundtrip"}
{"completed_files":201728,"completed_rows":199587530,"elapsed_seconds":40952.548,"stage":"roundtrip"}
{"completed_files":202752,"completed_rows":200311814,"elapsed_seconds":41097.261,"stage":"roundtrip"}
{"completed_files":203776,"completed_rows":201031418,"elapsed_seconds":41249.745,"stage":"roundtrip"}
{"completed_files":204800,"completed_rows":201751538,"elapsed_seconds":41406.738,"stage":"roundtrip"}
{"completed_files":205824,"completed_rows":202476180,"elapsed_seconds":41564.419,"stage":"roundtrip"}
{"completed_files":206848,"completed_rows":203195426,"elapsed_seconds":41717.076,"stage":"roundtrip"}
{"completed_files":207872,"completed_rows":203918693,"elapsed_seconds":41880.746,"stage":"roundtrip"}
{"completed_files":208896,"completed_rows":204637756,"elapsed_seconds":42032.24,"stage":"roundtrip"}
{"completed_files":209920,"completed_rows":205357518,"elapsed_seconds":42188.971,"stage":"roundtrip"}
{"completed_files":210944,"completed_rows":206075314,"elapsed_seconds":42333.929,"stage":"roundtrip"}
{"completed_files":211968,"completed_rows":206797150,"elapsed_seconds":42497.071,"stage":"roundtrip"}
{"completed_files":212992,"completed_rows":207517765,"elapsed_seconds":42668.656,"stage":"roundtrip"}
{"completed_files":214016,"completed_rows":208242143,"elapsed_seconds":42831.683,"stage":"roundtrip"}
{"completed_files":215040,"completed_rows":208962136,"elapsed_seconds":42991.331,"stage":"roundtrip"}
{"completed_files":216064,"completed_rows":209689646,"elapsed_seconds":43146.756,"stage":"roundtrip"}
{"completed_files":217088,"completed_rows":210110743,"elapsed_seconds":43231.712,"stage":"roundtrip"}
{"completed_files":218112,"completed_rows":210111118,"elapsed_seconds":43233.372,"stage":"roundtrip"}
{"completed_files":219136,"completed_rows":210111958,"elapsed_seconds":43236.68,"stage":"roundtrip"}
{"completed_files":220160,"completed_rows":210111958,"elapsed_seconds":43237.258,"stage":"roundtrip"}
{"completed_files":221184,"completed_rows":210111958,"elapsed_seconds":43237.83,"stage":"roundtrip"}
{"completed_files":222208,"completed_rows":210111958,"elapsed_seconds":43238.402,"stage":"roundtrip"}
{"completed_files":223232,"completed_rows":210111958,"elapsed_seconds":43238.965,"stage":"roundtrip"}
{"completed_files":224256,"completed_rows":210111958,"elapsed_seconds":43239.532,"stage":"roundtrip"}
{"completed_files":225280,"completed_rows":210111958,"elapsed_seconds":43240.099,"stage":"roundtrip"}
{"completed_files":226304,"completed_rows":210111958,"elapsed_seconds":43240.67,"stage":"roundtrip"}
{"completed_files":227328,"completed_rows":210111958,"elapsed_seconds":43241.237,"stage":"roundtrip"}
{"completed_files":228352,"completed_rows":210111958,"elapsed_seconds":43241.798,"stage":"roundtrip"}
{"completed_files":229376,"completed_rows":210111958,"elapsed_seconds":43242.384,"stage":"roundtrip"}
{"completed_files":230400,"completed_rows":210111958,"elapsed_seconds":43242.936,"stage":"roundtrip"}
{"completed_files":231424,"completed_rows":210111958,"elapsed_seconds":43243.494,"stage":"roundtrip"}
{"completed_files":232448,"completed_rows":210111958,"elapsed_seconds":43244.048,"stage":"roundtrip"}
{"completed_files":233472,"completed_rows":210111958,"elapsed_seconds":43244.603,"stage":"roundtrip"}
{"completed_files":234496,"completed_rows":210111958,"elapsed_seconds":43245.177,"stage":"roundtrip"}
{"completed_files":235520,"completed_rows":210111958,"elapsed_seconds":43245.743,"stage":"roundtrip"}
{"completed_files":236544,"completed_rows":210111958,"elapsed_seconds":43246.317,"stage":"roundtrip"}
{"completed_files":237568,"completed_rows":210111958,"elapsed_seconds":43246.88,"stage":"roundtrip"}
{"completed_files":238592,"completed_rows":210111958,"elapsed_seconds":43247.44,"stage":"roundtrip"}
{"completed_files":239616,"completed_rows":210111958,"elapsed_seconds":43248.002,"stage":"roundtrip"}
{"completed_files":240640,"completed_rows":210294693,"elapsed_seconds":43302.503,"stage":"roundtrip"}
{"completed_files":241664,"completed_rows":211015597,"elapsed_seconds":43544.42,"stage":"roundtrip"}
{"completed_files":242688,"completed_rows":211735628,"elapsed_seconds":43780.909,"stage":"roundtrip"}
{"completed_files":243712,"completed_rows":212459137,"elapsed_seconds":44030.158,"stage":"roundtrip"}
{"completed_files":244736,"completed_rows":213178824,"elapsed_seconds":44258.61,"stage":"roundtrip"}
{"completed_files":245760,"completed_rows":213892843,"elapsed_seconds":44484.889,"stage":"roundtrip"}
{"completed_files":246784,"completed_rows":214613206,"elapsed_seconds":44712.889,"stage":"roundtrip"}
{"completed_files":247808,"completed_rows":215335406,"elapsed_seconds":44942.14,"stage":"roundtrip"}
{"completed_files":248832,"completed_rows":216057086,"elapsed_seconds":45177.743,"stage":"roundtrip"}
{"completed_files":249856,"completed_rows":216772802,"elapsed_seconds":45405.935,"stage":"roundtrip"}
{"completed_files":250880,"completed_rows":217496447,"elapsed_seconds":45651.04,"stage":"roundtrip"}
{"completed_files":251904,"completed_rows":218217293,"elapsed_seconds":45886.413,"stage":"roundtrip"}
{"completed_files":252928,"completed_rows":218940960,"elapsed_seconds":46110.738,"stage":"roundtrip"}
{"completed_files":253952,"completed_rows":219656833,"elapsed_seconds":46373.273,"stage":"roundtrip"}
{"completed_files":254976,"completed_rows":220379230,"elapsed_seconds":46617.362,"stage":"roundtrip"}
{"completed_files":256000,"completed_rows":221094477,"elapsed_seconds":46843.175,"stage":"roundtrip"}
{"completed_files":257024,"completed_rows":221816375,"elapsed_seconds":47071.702,"stage":"roundtrip"}
{"completed_files":258048,"completed_rows":222535604,"elapsed_seconds":47305.302,"stage":"roundtrip"}
{"completed_files":259072,"completed_rows":223260066,"elapsed_seconds":47561.868,"stage":"roundtrip"}
{"completed_files":260096,"completed_rows":223983361,"elapsed_seconds":47807.038,"stage":"roundtrip"}
{"completed_files":261120,"completed_rows":224705701,"elapsed_seconds":48032.727,"stage":"roundtrip"}
{"completed_files":262144,"completed_rows":225237781,"elapsed_seconds":48195.842,"stage":"roundtrip"}
{"completed_files":263168,"completed_rows":225237781,"elapsed_seconds":48196.458,"stage":"roundtrip"}
{"completed_files":264192,"completed_rows":225237781,"elapsed_seconds":48197.06,"stage":"roundtrip"}
{"completed_files":265216,"completed_rows":225237781,"elapsed_seconds":48197.65,"stage":"roundtrip"}
{"completed_files":266240,"completed_rows":225237980,"elapsed_seconds":48198.854,"stage":"roundtrip"}
{"completed_files":267264,"completed_rows":225239178,"elapsed_seconds":48203.06,"stage":"roundtrip"}
{"completed_files":268288,"completed_rows":225240284,"elapsed_seconds":48207.241,"stage":"roundtrip"}
{"completed_files":269312,"completed_rows":225241390,"elapsed_seconds":48211.296,"stage":"roundtrip"}
{"completed_files":270336,"completed_rows":225242586,"elapsed_seconds":48215.153,"stage":"roundtrip"}
{"completed_files":271360,"completed_rows":225242586,"elapsed_seconds":48215.697,"stage":"roundtrip"}
{"completed_files":272384,"completed_rows":225242586,"elapsed_seconds":48216.256,"stage":"roundtrip"}
{"completed_files":273408,"completed_rows":225242586,"elapsed_seconds":48216.809,"stage":"roundtrip"}
{"completed_files":274432,"completed_rows":225242586,"elapsed_seconds":48217.352,"stage":"roundtrip"}
{"completed_files":275456,"completed_rows":225242586,"elapsed_seconds":48217.89,"stage":"roundtrip"}
{"completed_files":276480,"completed_rows":225242586,"elapsed_seconds":48218.433,"stage":"roundtrip"}
{"completed_files":277504,"completed_rows":225242586,"elapsed_seconds":48218.975,"stage":"roundtrip"}
{"completed_files":278528,"completed_rows":225242586,"elapsed_seconds":48219.51,"stage":"roundtrip"}
{"completed_files":279552,"completed_rows":225242586,"elapsed_seconds":48220.059,"stage":"roundtrip"}
{"completed_files":280576,"completed_rows":225242586,"elapsed_seconds":48220.6,"stage":"roundtrip"}
{"completed_files":281600,"completed_rows":225242586,"elapsed_seconds":48221.153,"stage":"roundtrip"}
{"completed_files":282624,"completed_rows":225242586,"elapsed_seconds":48221.68,"stage":"roundtrip"}
{"completed_files":283648,"completed_rows":225242586,"elapsed_seconds":48222.216,"stage":"roundtrip"}
{"completed_files":284672,"completed_rows":225242586,"elapsed_seconds":48222.745,"stage":"roundtrip"}
{"completed_files":285696,"completed_rows":225242586,"elapsed_seconds":48223.279,"stage":"roundtrip"}
{"completed_files":286720,"completed_rows":225245831,"elapsed_seconds":48224.686,"stage":"roundtrip"}
{"completed_files":287744,"completed_rows":225275931,"elapsed_seconds":48233.243,"stage":"roundtrip"}
{"completed_files":288768,"completed_rows":225305957,"elapsed_seconds":48241.62,"stage":"roundtrip"}
{"completed_files":289792,"completed_rows":225335963,"elapsed_seconds":48249.976,"stage":"roundtrip"}
{"completed_files":290816,"completed_rows":225365871,"elapsed_seconds":48258.762,"stage":"roundtrip"}
{"completed_files":291840,"completed_rows":225395879,"elapsed_seconds":48267.704,"stage":"roundtrip"}
{"completed_files":292864,"completed_rows":225425952,"elapsed_seconds":48276.098,"stage":"roundtrip"}
{"completed_files":293888,"completed_rows":225455703,"elapsed_seconds":48284.426,"stage":"roundtrip"}
{"completed_files":294912,"completed_rows":225485755,"elapsed_seconds":48292.825,"stage":"roundtrip"}
{"completed_files":295936,"completed_rows":225515973,"elapsed_seconds":48301.353,"stage":"roundtrip"}
{"completed_files":296960,"completed_rows":225545732,"elapsed_seconds":48309.899,"stage":"roundtrip"}
{"completed_files":297984,"completed_rows":225575634,"elapsed_seconds":48318.498,"stage":"roundtrip"}
{"completed_files":299008,"completed_rows":225605649,"elapsed_seconds":48327.514,"stage":"roundtrip"}
{"completed_files":300032,"completed_rows":225635562,"elapsed_seconds":48336.144,"stage":"roundtrip"}
{"completed_files":301056,"completed_rows":225665564,"elapsed_seconds":48344.79,"stage":"roundtrip"}
{"completed_files":302080,"completed_rows":225695244,"elapsed_seconds":48353.899,"stage":"roundtrip"}
{"completed_files":303104,"completed_rows":225721926,"elapsed_seconds":48363.586,"stage":"roundtrip"}
{"completed_files":304128,"completed_rows":225721926,"elapsed_seconds":48364.126,"stage":"roundtrip"}
{"completed_files":305152,"completed_rows":225721926,"elapsed_seconds":48364.673,"stage":"roundtrip"}
{"completed_files":306176,"completed_rows":225722996,"elapsed_seconds":48367.439,"stage":"roundtrip"}
{"completed_files":307200,"completed_rows":225724811,"elapsed_seconds":48371.665,"stage":"roundtrip"}
{"completed_files":308224,"completed_rows":225726552,"elapsed_seconds":48375.68,"stage":"roundtrip"}
{"completed_files":309248,"completed_rows":225726552,"elapsed_seconds":48376.278,"stage":"roundtrip"}
{"completed_files":310272,"completed_rows":225726552,"elapsed_seconds":48376.851,"stage":"roundtrip"}
{"completed_files":311296,"completed_rows":225726552,"elapsed_seconds":48377.42,"stage":"roundtrip"}
{"completed_files":312320,"completed_rows":225726883,"elapsed_seconds":48379.046,"stage":"roundtrip"}
{"completed_files":313344,"completed_rows":240773576,"elapsed_seconds":50319.395,"stage":"roundtrip"}
{"completed_files":314368,"completed_rows":266988456,"elapsed_seconds":53763.806,"stage":"roundtrip"}
{"completed_files":315392,"completed_rows":709538229,"elapsed_seconds":118169.5,"stage":"roundtrip"}
{"completed_files":316416,"completed_rows":1164857644,"elapsed_seconds":188777.712,"stage":"roundtrip"}
{"completed_files":317440,"completed_rows":1164857644,"elapsed_seconds":188778.259,"stage":"roundtrip"}
{"completed_files":318464,"completed_rows":1164857644,"elapsed_seconds":188778.779,"stage":"roundtrip"}
{"completed_files":319488,"completed_rows":1164857644,"elapsed_seconds":188779.297,"stage":"roundtrip"}
{"completed_files":320512,"completed_rows":1164857644,"elapsed_seconds":188779.824,"stage":"roundtrip"}
{"completed_files":321536,"completed_rows":1164857644,"elapsed_seconds":188780.361,"stage":"roundtrip"}
{"completed_files":322560,"completed_rows":1164857644,"elapsed_seconds":188780.958,"stage":"roundtrip"}
{"completed_files":323584,"completed_rows":1164857644,"elapsed_seconds":188781.488,"stage":"roundtrip"}
{"completed_files":324608,"completed_rows":1164857644,"elapsed_seconds":188782.041,"stage":"roundtrip"}
{"completed_files":325632,"completed_rows":1164857644,"elapsed_seconds":188782.581,"stage":"roundtrip"}
{"completed_files":326656,"completed_rows":1164857644,"elapsed_seconds":188783.117,"stage":"roundtrip"}
{"completed_files":327680,"completed_rows":1164857644,"elapsed_seconds":188783.644,"stage":"roundtrip"}
{"completed_files":328704,"completed_rows":1164857644,"elapsed_seconds":188784.182,"stage":"roundtrip"}
{"completed_files":329728,"completed_rows":1164857644,"elapsed_seconds":188784.709,"stage":"roundtrip"}
{"completed_files":330752,"completed_rows":1164857644,"elapsed_seconds":188785.23,"stage":"roundtrip"}
{"completed_files":331776,"completed_rows":1164857644,"elapsed_seconds":188785.746,"stage":"roundtrip"}
{"completed_files":332800,"completed_rows":1164857644,"elapsed_seconds":188786.266,"stage":"roundtrip"}
{"completed_files":333824,"completed_rows":1164857644,"elapsed_seconds":188786.812,"stage":"roundtrip"}
{"completed_files":334848,"completed_rows":1164857644,"elapsed_seconds":188787.344,"stage":"roundtrip"}
{"completed_files":335872,"completed_rows":1164857644,"elapsed_seconds":188787.879,"stage":"roundtrip"}
{"completed_files":336896,"completed_rows":1164857644,"elapsed_seconds":188788.414,"stage":"roundtrip"}
{"completed_files":337920,"completed_rows":1164857644,"elapsed_seconds":188788.959,"stage":"roundtrip"}
{"completed_files":338944,"completed_rows":1164857644,"elapsed_seconds":188789.48,"stage":"roundtrip"}
{"completed_files":339968,"completed_rows":1164857644,"elapsed_seconds":188790.003,"stage":"roundtrip"}
{"completed_files":340992,"completed_rows":1164857644,"elapsed_seconds":188790.548,"stage":"roundtrip"}
{"completed_files":342016,"completed_rows":1164857644,"elapsed_seconds":188791.076,"stage":"roundtrip"}
{"completed_files":343040,"completed_rows":1164857644,"elapsed_seconds":188791.604,"stage":"roundtrip"}
{"completed_files":344064,"completed_rows":1164857644,"elapsed_seconds":188792.122,"stage":"roundtrip"}
{"completed_files":345088,"completed_rows":1164857644,"elapsed_seconds":188792.645,"stage":"roundtrip"}
{"completed_files":346112,"completed_rows":1164857644,"elapsed_seconds":188793.179,"stage":"roundtrip"}
{"completed_files":347136,"completed_rows":1164857644,"elapsed_seconds":188793.712,"stage":"roundtrip"}
{"completed_files":348160,"completed_rows":1164857644,"elapsed_seconds":188794.24,"stage":"roundtrip"}
{"completed_files":349184,"completed_rows":1164857644,"elapsed_seconds":188794.773,"stage":"roundtrip"}
{"completed_files":350208,"completed_rows":1164857644,"elapsed_seconds":188795.319,"stage":"roundtrip"}
{"completed_files":351232,"completed_rows":1164857644,"elapsed_seconds":188795.85,"stage":"roundtrip"}
{"completed_files":352256,"completed_rows":1164857644,"elapsed_seconds":188796.388,"stage":"roundtrip"}
{"completed_files":353280,"completed_rows":1164857644,"elapsed_seconds":188796.924,"stage":"roundtrip"}
{"completed_files":354304,"completed_rows":1164857644,"elapsed_seconds":188797.457,"stage":"roundtrip"}
{"completed_files":355328,"completed_rows":1164857644,"elapsed_seconds":188797.988,"stage":"roundtrip"}
{"completed_files":356352,"completed_rows":1164857644,"elapsed_seconds":188798.521,"stage":"roundtrip"}
{"completed_files":357376,"completed_rows":1164857644,"elapsed_seconds":188799.056,"stage":"roundtrip"}
{"completed_files":358400,"completed_rows":1164857644,"elapsed_seconds":188799.645,"stage":"roundtrip"}
{"completed_files":359424,"completed_rows":1164857644,"elapsed_seconds":188800.185,"stage":"roundtrip"}
{"completed_files":360448,"completed_rows":1164857644,"elapsed_seconds":188800.718,"stage":"roundtrip"}
{"completed_files":361472,"completed_rows":1164857644,"elapsed_seconds":188801.248,"stage":"roundtrip"}
{"completed_files":362496,"completed_rows":1164857644,"elapsed_seconds":188801.781,"stage":"roundtrip"}
{"completed_files":363520,"completed_rows":1164857644,"elapsed_seconds":188802.312,"stage":"roundtrip"}
{"completed_files":364544,"completed_rows":1164857644,"elapsed_seconds":188802.842,"stage":"roundtrip"}
{"completed_files":365568,"completed_rows":1164857644,"elapsed_seconds":188803.379,"stage":"roundtrip"}
{"completed_files":366592,"completed_rows":1164857644,"elapsed_seconds":188803.911,"stage":"roundtrip"}
{"completed_files":367616,"completed_rows":1164857644,"elapsed_seconds":188804.437,"stage":"roundtrip"}
{"completed_files":368640,"completed_rows":1164857644,"elapsed_seconds":188804.984,"stage":"roundtrip"}
{"completed_files":369664,"completed_rows":1164857644,"elapsed_seconds":188805.515,"stage":"roundtrip"}
{"completed_files":370688,"completed_rows":1164857644,"elapsed_seconds":188806.051,"stage":"roundtrip"}
{"completed_files":371712,"completed_rows":1164857644,"elapsed_seconds":188806.59,"stage":"roundtrip"}
{"completed_files":372736,"completed_rows":1164857644,"elapsed_seconds":188807.123,"stage":"roundtrip"}
{"completed_files":373760,"completed_rows":1164857644,"elapsed_seconds":188807.657,"stage":"roundtrip"}
{"completed_files":374784,"completed_rows":1164857644,"elapsed_seconds":188808.196,"stage":"roundtrip"}
{"completed_files":375808,"completed_rows":1164857644,"elapsed_seconds":188808.728,"stage":"roundtrip"}
{"completed_files":376832,"completed_rows":1164857644,"elapsed_seconds":188809.267,"stage":"roundtrip"}
{"completed_files":377856,"completed_rows":1164857644,"elapsed_seconds":188809.801,"stage":"roundtrip"}
{"completed_files":378880,"completed_rows":1164857644,"elapsed_seconds":188810.32,"stage":"roundtrip"}
{"completed_files":379904,"completed_rows":1164857644,"elapsed_seconds":188810.856,"stage":"roundtrip"}
{"completed_files":380928,"completed_rows":1164857644,"elapsed_seconds":188811.424,"stage":"roundtrip"}
{"completed_files":381952,"completed_rows":1164857644,"elapsed_seconds":188811.981,"stage":"roundtrip"}
{"completed_files":382976,"completed_rows":1164857644,"elapsed_seconds":188812.53,"stage":"roundtrip"}
{"completed_files":384000,"completed_rows":1164857644,"elapsed_seconds":188813.073,"stage":"roundtrip"}
{"completed_files":385024,"completed_rows":1164857644,"elapsed_seconds":188813.621,"stage":"roundtrip"}
{"completed_files":386048,"completed_rows":1164857644,"elapsed_seconds":188814.168,"stage":"roundtrip"}
{"completed_files":387072,"completed_rows":1164857644,"elapsed_seconds":188814.715,"stage":"roundtrip"}
{"completed_files":388096,"completed_rows":1164857644,"elapsed_seconds":188815.267,"stage":"roundtrip"}
{"completed_files":389120,"completed_rows":1164857644,"elapsed_seconds":188815.815,"stage":"roundtrip"}
{"completed_files":390144,"completed_rows":1164857644,"elapsed_seconds":188816.364,"stage":"roundtrip"}
{"completed_files":391168,"completed_rows":1164857644,"elapsed_seconds":188816.907,"stage":"roundtrip"}
{"completed_files":392192,"completed_rows":1164857644,"elapsed_seconds":188817.457,"stage":"roundtrip"}
{"completed_files":393216,"completed_rows":1164857772,"elapsed_seconds":188818.403,"stage":"roundtrip"}
{"completed_files":394240,"completed_rows":1164858890,"elapsed_seconds":188822.187,"stage":"roundtrip"}
{"completed_files":395264,"completed_rows":1164860570,"elapsed_seconds":188826.01,"stage":"roundtrip"}
{"completed_files":396288,"completed_rows":1164862373,"elapsed_seconds":188829.825,"stage":"roundtrip"}
{"completed_files":397312,"completed_rows":1164864048,"elapsed_seconds":188833.657,"stage":"roundtrip"}
{"completed_files":398336,"completed_rows":1164865243,"elapsed_seconds":188837.457,"stage":"roundtrip"}
{"completed_files":399360,"completed_rows":1164866351,"elapsed_seconds":188841.388,"stage":"roundtrip"}
{"completed_files":400384,"completed_rows":1164867461,"elapsed_seconds":188845.199,"stage":"roundtrip"}
{"completed_files":401408,"completed_rows":1164870771,"elapsed_seconds":188849.579,"stage":"roundtrip"}
{"completed_files":402432,"completed_rows":1164884670,"elapsed_seconds":188855.075,"stage":"roundtrip"}
{"completed_files":403456,"completed_rows":1164906178,"elapsed_seconds":188861.305,"stage":"roundtrip"}
{"completed_files":404480,"completed_rows":1164916741,"elapsed_seconds":188866.234,"stage":"roundtrip"}
{"completed_files":405504,"completed_rows":1164925808,"elapsed_seconds":188871.001,"stage":"roundtrip"}
{"completed_files":406528,"completed_rows":1164925864,"elapsed_seconds":188871.722,"stage":"roundtrip"}
{"completed_files":407552,"completed_rows":1164925864,"elapsed_seconds":188872.279,"stage":"roundtrip"}
{"completed_files":408576,"completed_rows":1164925864,"elapsed_seconds":188872.829,"stage":"roundtrip"}
{"completed_files":409600,"completed_rows":1164925864,"elapsed_seconds":188873.384,"stage":"roundtrip"}
{"completed_files":410624,"completed_rows":1164926146,"elapsed_seconds":188874.849,"stage":"roundtrip"}
{"completed_files":411648,"completed_rows":1164927786,"elapsed_seconds":188879.452,"stage":"roundtrip"}
{"completed_files":412672,"completed_rows":1164929312,"elapsed_seconds":188883.906,"stage":"roundtrip"}
{"completed_files":413696,"completed_rows":1164930658,"elapsed_seconds":188888.318,"stage":"roundtrip"}
{"completed_files":414720,"completed_rows":1164933603,"elapsed_seconds":188893.032,"stage":"roundtrip"}
{"completed_files":415744,"completed_rows":1164934181,"elapsed_seconds":188895.407,"stage":"roundtrip"}
{"completed_files":416768,"completed_rows":1164934181,"elapsed_seconds":188895.999,"stage":"roundtrip"}
{"completed_files":417792,"completed_rows":1164934181,"elapsed_seconds":188896.564,"stage":"roundtrip"}
{"completed_files":418816,"completed_rows":1164934181,"elapsed_seconds":188897.112,"stage":"roundtrip"}
{"completed_files":419840,"completed_rows":1164934318,"elapsed_seconds":188898.057,"stage":"roundtrip"}
{"completed_files":420864,"completed_rows":1164935342,"elapsed_seconds":188901.671,"stage":"roundtrip"}
{"completed_files":421888,"completed_rows":1164936366,"elapsed_seconds":188905.165,"stage":"roundtrip"}
{"completed_files":422912,"completed_rows":1164937390,"elapsed_seconds":188908.749,"stage":"roundtrip"}
{"bundle_bytes":13232150,"completed_files":423446,"completed_rows":1165116869,"elapsed_seconds":189195.734,"metadata_charge_bytes":3950355317,"nautilus_version":"2.0.0rc3","proof_bytes":264156517,"proof_path":"/home/lars/Crypto_Multifactor_Bot/data/.cex002_harmonic_bundle/.proofs/3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d.json","proof_sha256":"3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d","scratch_bytes":0,"sqlite_bytes":3458088960,"stage":"PASS"}
```

Checker/deadline exit status: 0
Output capture exit status: 0

## Provenance

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 517 `research/sprint_004/517_CEX002_FULL_CONSUMER_EXECUTION_AUTHORIZATION.md`

The owner's continuation authorized the reviewer to advance CEX-002; Review 517
authorizes Hermes to execute the integrated checker ONCE over the entire accepted
candidate. No developer or source change was needed and none was made.

Execution HEAD at launch: `2e7fadb34e2a434c44da6502c617c97490f04f47` (record header,
captured by the reviewed bash block itself). A later reviewer governance commit
`cbcdca80833383c1ac5d557dd1979dc7ce8f0246` advanced repository HEAD; the execution
remained bound to `2e7fadb`.

Process identity: session_id `proc_0c886acde04a`, PID `2343463`, launched
2026-10-21T05:01:23Z, run with native `terminal(background=true, notify_on_complete=true,
pty=false)`. Completion notice: **exit code 0**.

Governing command (the exact Review 517 bash block, run once):

```
cd /home/lars/Crypto_Multifactor_Bot
set -euo pipefail
record=research/sprint_004/518_CEX002_FULL_CONSUMER_EXECUTION_RECORD.md
if [ -e "$record" ] || [ -L "$record" ]; then
    printf 'Record 518 already exists or is a symlink\n' >&2
    exit 1
fi
set -o noclobber
exec 3> "$record"
set +o noclobber
exec 4>> /dev/fd/3
exec 3>&-
printf '# CEX-002 Record 518 — Full consumer execution\n\nLaunch UTC: ' >&4
date -u +'%Y-%m-%dT%H:%M:%SZ' >&4
printf 'Execution HEAD: ' >&4
git rev-parse HEAD >&4
printf '\n## Raw checker output\n\n```jsonl\n' >&4
set +e
PYTHONPATH=src /usr/bin/timeout --signal=TERM --kill-after=60s 345600s /tmp/cex002_nautilus_review511_env/bin/python -u scripts/research/check_cex002_nautilus_consumer.py --repo /home/lars/Crypto_Multifactor_Bot --candidate-sha 8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34 --checker-sha ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117 --scratch-root /home/lars/.cache/tmp/cex002_review517_full_consumer_scratch 2>&1 | tee -a /dev/fd/4
pipeline_status=("${PIPESTATUS[@]}")
checker_status=${pipeline_status[0]}
capture_status=${pipeline_status[1]}
printf '```\n\nChecker/deadline exit status: %s\nOutput capture exit status: %s\n' "$checker_status" "$capture_status" >&4 || exit 1
exec 4>&-
if [ "$capture_status" -ne 0 ]; then
    exit "$capture_status"
fi
exit "$checker_status"
```

## Preflight (grouped, read-only, one pass, 2026-10-21T04:57:23Z)

Observed before launch: HEAD == origin/main == `2e7fadb…`, index empty; checker
`ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117` and test
`c4e051a1b9e0f9ae9df983f4319c2f4370cbe108b2d88b2632af8768d4465ff5`; the three
runtime sources equal to their blobs at `1f5629b`
(`cex002_reference_release.py` fed0d0ef49eb3704be577a378dfd12eb7e6876fc41fbfe9d6507e7ef5b83fe00,
`binance_usdm_harmonic_bundle.py` 1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b,
`publish_binance_usdm_harmonic_bundle.py` cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9);
prepared descriptor physical SHA equals its filename
`8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34`; `.proofs`,
fresh scratch root and Record 518 all absent and non-symlink (`-L` explicit); environment
executable and `/usr/bin/timeout` present; 299,267,674,112 bytes SSD available; no real
checker process (native `ps` count 0; an earlier count of 1 was the preflight shell itself).

Read-only SQLite mode=ro queries, canonical `json.dumps(rows, default=str,
separators=(',',':'), ensure_ascii=False)` + SHA256 UTF8, before launch:
Q0 count 0 / `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`;
Q1 count 5 / `b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103`.
Both matched the accepted pins.

## Terminal status (from the raw block above)

- Checker/deadline exit status: **0**; output capture exit status: **0**.
- Checker terminal stage: **PASS** with `completed_files` 423446 and `completed_rows`
  1,165,116,869; `scratch_bytes` 0; `bundle_bytes` 13232150; `sqlite_bytes` 3458088960;
  `metadata_charge_bytes` 3950355317; `nautilus_version` 2.0.0rc3; `elapsed_seconds`
  189195.734 (≈ 52.55 h wall clock, within the 345600 s / 96 h deadline).
- Elapsed `roundtrip` progress is retained verbatim in the raw block (415 jsonl stage
  lines). The retained progress lines show `completed_files` advancing faster than
  `completed_rows` during traversal; that is the checker's own emission and is not
  interpreted or corrected here. The checker's terminal `completed_files`/
  `completed_rows` and its own closure assertions are the authoritative totals.

## Terminal proof inspection (review step 4)

Emitted proof: `data/.cex002_harmonic_bundle/.proofs/3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d.json`
- Physical size 264,156,517 bytes; physical SHA256
  `3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d` — equals the
  `proof_sha256` and the filename.
- Root contract keys: exactly `candidate_sha256, checker_source_sha256, datasets,
  document_type, nautilus_version, schema_version, scope, status`.
- `document_type` `cex002_harmonic_bundle_consumer_proof`, `schema_version` 1, `status`
  `PASS`, `scope` `complete_release`, `candidate_sha256`
  `8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34`, `checker_source_sha256`
  `ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117`, `nautilus_version`
  2.0.0rc3.
- Datasets: 11. Per-dataset reconciliation: every component has matching
  `source_row_count`/`readback_row_count` and matching
  `source_value_sha256`/`roundtrip_value_sha256` (0 mismatches across all datasets).
- Component closure: 423,446 components = 178,947 table components + 244,499 metadata
  components. Total table rows summed over the emitted components: **1,165,116,869**,
  matching the accepted release row count exactly.
- Candidate descriptor reauthenticated after the run: physical SHA
  `8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34` (unchanged).
- Checker source reauthenticated: `ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117`
  at `2e7fadb` and in the worktree (unchanged).
- Final scratch root `/home/lars/.cache/tmp/cex002_review517_full_consumer_scratch`:
  0 entries, 0 bytes.

## Terminal catalog re-query (review step 4)

Read-only mode=ro queries repeated after the run:
Q0 count 0 / `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`;
Q1 count 5 / `b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103`.
Both unchanged from preflight — no catalog mutation occurred and no catalog admission was
performed.

## Limitations

- The proof is a complete-release consumer proof for the accepted non-consumable candidate;
  it does **not** admit the release to the production catalog and does not by itself
  constitute final ticket acceptance. Prepared candidate remains non-consumable.
- The emitted proof is stored under `data/` and is gitignored; only this record is
  published. No proof file is staged or committed.
- No producer run, replay, economic/final suite, second full traversal or extra verifier
  was executed. No catalog admission, cleanup, repair or retry.
- Fixture acceptance (27 passed) and the prior bounded Record 516 measurement are preserved,
  not rerun. Unrelated dirty working-tree paths are preserved unchanged.
- This record makes no claim beyond what the accepted checker itself emitted and sealed.

## Record status

Record 518 is full-consumer-execution evidence owned by Hermes. CEX-002 remains
IN_PROGRESS; next ticket NONE; reviewer acceptance remains exclusive.
