from .agent_based_api.v1 import *

from .agent_based_api.v1.type_defs import *

from .utils import (
    temperature
)

"""
iso.3.6.1.2.1.33.1.13.1.0 = INTEGER: 1
iso.3.6.1.2.1.33.1.13.2.0 = INTEGER: 0
iso.3.6.1.2.1.33.1.13.3.0 = INTEGER: 0
iso.3.6.1.2.1.33.1.13.4.0 = INTEGER: 0
iso.3.6.1.2.1.33.1.13.10.0 = INTEGER: 42
iso.3.6.1.2.1.33.1.13.11.1.0 = INTEGER: 0
iso.3.6.1.2.1.33.1.13.11.2.0 = INTEGER: 1
iso.3.6.1.2.1.33.1.13.11.3.1.2.1 = INTEGER: 0
iso.3.6.1.2.1.33.1.13.11.3.1.3.1 = INTEGER: 0
iso.3.6.1.2.1.33.1.13.11.3.1.5.1 = INTEGER: 4
iso.3.6.1.2.1.33.1.13.12.1.0 = INTEGER: 1
iso.3.6.1.2.1.33.1.13.12.2.1.2.1 = INTEGER: 50
iso.3.6.1.2.1.33.1.13.14.1.0 = INTEGER: 1
iso.3.6.1.2.1.33.1.13.14.2.1.2.1 = INTEGER: 50
"""

oids = {
    #'1.0': 'Source1On',
    '1.0': 'OutputSource1On',
    #'2.0': 'Source2On',
    '2.0': 'OutputSource2On',
    '3.0': 'Source1ManualBypassOn',
    '4.0': 'Source2ManualBypassOn',
    '10.0': 'Temperature',
    #'11.2.0': 'OutputNumLines',
    '11.3.1.5.1': 'OutputPercentLoad',
    #'12.1.0': 'Source1InputNumLines',
    '12.2.1.2.1': 'Source1InputFrequency',
    #'14.1.0': 'Source2InputNumLines',
    '14.2.1.2.1': 'Source2InputFrequency',
}

def parse_riello_ats(string_table):
    res = dict()
    services = ["Source1", "Source2", "Output"]
    for srv in services:
        res[srv] = dict()
    for name in oids.values():
        value = string_table[0].pop(0)
        if name == "Temperature":
            res[name] = value
        for srv in services:
            if name.startswith(srv):
                name = name.replace(srv,"")
                res[srv][name] = value
    return res

def discover_riello_ats_temp(section):
    if "Temperature" in section:
        yield Service(item="Temperature")

def check_riello_ats_temp(item, params, section):
    if data := section.get(item, None):
        yield from check_levels(
            value = float(data),
            metric_name = "temp",
            label = "Device Temperature",
            levels_upper = params["upper"],
            render_func = lambda temp : f"{temp} °C"
        )
    
def discover_riello_ats_source(section):
    for item in section:
        if item.startswith("Source"):
            yield Service(item=item)

def check_riello_ats_source(item, section):
    if data := section.get(item):
        value = int(data["InputFrequency"])
        manual = bool(int(data["ManualBypassOn"]))
        if value == 0:
            yield Result(state = State.CRIT, summary=f"{item} not connected(!!!)")
        else:
            yield Result(state = State.OK, summary=f"{item} input frequency {value}Hz")
        if manual:
            yield Result(state = State.WARN, summary=f"{item} manual bypass active(!)")
        else:
            yield Result(state = State.OK, summary=f"{item} not bypassed.")

def discover_riello_ats_output(section):
    for item in section:
        if item.startswith("Output"):
            yield Service(item=item)
            
def check_riello_ats_output(item, params, section):
    if data := section.get(item):
        load = float(data["PercentLoad"])
        yield from check_levels(
            value = load,
            metric_name = "output_load",
            label = "Output Load",
            levels_upper = params["upper"],
            render_func = lambda x : f"{x}%"
        )
        # todo: warning when source of output changes?

register.snmp_section(
    name='rielloats',
    fetch = SNMPTree( base=".1.3.6.1.2.1.33.1.13", oids=list(oids.keys())),
    detect = contains(".1.3.6.1.2.1.33.1.1.2.0", "ATS"),
    parse_function = parse_riello_ats,
)

register.check_plugin(
    name = 'rielloats_temp',
    sections=['rielloats'],
    service_name = "%s",
    check_ruleset_name = "temperature",
    check_default_parameters = {"upper": (40.0, 50.0)},
    discovery_function = discover_riello_ats_temp,
    check_function = check_riello_ats_temp,
)

register.check_plugin(
    name = 'rielloats_output',
    sections=['rielloats'],
    service_name = "%s",
    check_ruleset_name = 'ups_out_load',
    check_default_parameters = {"upper": (70.0, 80.0)},
    discovery_function = discover_riello_ats_output,
    check_function = check_riello_ats_output,
)

register.check_plugin(
    name = 'rielloats_source',
    sections=['rielloats'],
    service_name = "%s",
    discovery_function = discover_riello_ats_source,
    check_function = check_riello_ats_source,
)

