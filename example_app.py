from example_samplers import *
from apic import  CliCPU, CliIP

leaf1 = '10.126.216.230'
leaf2 = '10.126.216.231'
spine1 = '10.126.216.71'


def run(app, xyzzy):
    samplers = [
        SynergySampler(xyzzy, 3),
        BuzzwordsSampler(xyzzy, 2),
        ConvergenceSampler(xyzzy, 1),
        CliCPU(xyzzy,1,leaf1,'cli_cpu_l1',1),
        CliCPU(xyzzy,1,leaf2,'cli_cpu_l2',1),
        CliCPU(xyzzy,1,spine1,'cli_cpu_s1',0),
        CliIP(xyzzy,5,spine1,'cli_ip_s1',1),
        CliIP(xyzzy,5,leaf1,'cli_ip_l1',1),
        CliIP(xyzzy,5,leaf2,'cli_ip_l2',1)
    ]

    try:
        app.run(debug=True,
                port=5000,
                host='0.0.0.0',
                threaded=True,
                use_reloader=False,
                use_debugger=True
                )
    finally:
        print "Disconnecting clients"
        xyzzy.stopped = True
        
        print "Stopping %d timers" % len(samplers)
        for (i, sampler) in enumerate(samplers):
            sampler.stop()

    print "Done"
