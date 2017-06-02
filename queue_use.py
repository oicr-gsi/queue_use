#!/usr/bin/env python
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

DEBUG=0

# What do I want?
# How busy the queue is as a whole (requested h_vmem/total available mem)
# How busy particular machine sizes are (16G, 24G, 125.1, 252.3, 220.8)
# how hoggy our processes are being (requested vs actual)

def main(queue, pretty, prometheus):
    qstat=parse_qstat()
    qh = parse_qhost()
    machine_size={}
    total_hvmem=0
    total_memtotal=0
    total_maxvmem=0
    for host in qh.getroot():
        for q in host.iter('queue'):
            if q.attrib['name'] == queue:
                row=collect_stats(host, qstat, queue)
                hvmem=row['h_vmem']
                memtotal=row['mem_total']
                maxvmem=row['maxvmem']
                total_hvmem+=hvmem
                total_memtotal+=memtotal
                total_maxvmem+=maxvmem
                if not memtotal in machine_size:
                    machine_size[memtotal]={'h_vmem':0, 'mem_total':0, 'maxvmem':0}
                machine_size[memtotal]['h_vmem']+=hvmem
                machine_size[memtotal]['mem_total']+=memtotal
                machine_size[memtotal]['maxvmem']+=maxvmem
    if pretty:
        pretty_print(machine_size,total_hvmem,total_memtotal,total_maxvmem)
    if prometheus is not None:
        send_to_prometheus(queue,machine_size,prometheus)

def send_to_prometheus(queue,machine_size,prometheus):
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
    registry = CollectorRegistry()
    g_maxvmem = Gauge('sgequeue_maxvmem', 'The current maximum virtual memory (bytes) used on the given queue', ['nodesize'], registry=registry)
    g_hvmem = Gauge('sgequeue_hvmem', 'The current requested virtual memory (bytes) used on the given queue', ['nodesize'], registry=registry)
    g_memtotal = Gauge('sgequeue_memtotal', 'The current maximum virtual memory (bytes) available on the given queue', ['nodesize'], registry=registry)
   
    for size in machine_size:
        sizerow=machine_size[size]
        nodesize=str(get_gigs(size))
        g_maxvmem.labels(nodesize).set(sizerow['maxvmem'])
        g_hvmem.labels(nodesize).set(sizerow['h_vmem'])
        g_memtotal.labels(nodesize).set(sizerow['mem_total'])

    push_to_gateway(prometheus, job=queue, registry=registry)


def pretty_print(machine_size,total_hvmem,total_memtotal,total_maxvmem):
        print "{0:<20s}{1:<20s}{2:<20s}{3:<20s}{4:<20s}{5:<20s}".format("Node Size (G)","Busy-ness (%)","Requested (G)","Total (G)","Used (G)","Efficiency (%)")
        for size in machine_size:
                sizerow=machine_size[size]
                nodesize=str(get_gigs(size))
                busyness=(100.0*safe_div(sizerow['h_vmem'],sizerow['mem_total']))
                requestedg=get_gigs(sizerow['h_vmem'])
                totalg=get_gigs(sizerow['mem_total'])
                usedg=get_gigs(sizerow['maxvmem'])
                efficiency=(100*safe_div(usedg,requestedg))
                print "{0:<20s}{1:<20.2f}{2:<20.2f}{3:<20.2f}{4:<20.2f}{5:<20.2f}".format(nodesize,busyness,requestedg,totalg,usedg,efficiency)

        total_busyness=(100.0*safe_div(total_hvmem,total_memtotal))
        total_efficiency=(100.0*safe_div(total_maxvmem,total_hvmem))
        print "{5:<20s}{0:<20.2f}{1:<20.2f}{2:<20.2f}{3:<20.2f}{4:20.2f}".format(total_busyness,get_gigs(total_hvmem),get_gigs(total_memtotal),get_gigs(total_maxvmem),total_efficiency,"Total")



def safe_div(num, denom):
# Because I'm too lazy to check for a 0 denominator every time I divide
    if denom != 0:
        return num/denom
    else:
        return 0

def parse_qhost():
    qh_file="qhosts.xml"
    if not DEBUG:
        import tempfile,subprocess
        tmpfile=tempfile.NamedTemporaryFile()
        subprocess.call(['qhost','-xml','-q','-j','-F'], stdout=tmpfile)
        qh_file=tmpfile.name
    return ET.parse(qh_file)



def parse_qstat():
# Parsing the qstat XML log because I don't want to have to iterate
# through the file for every job mentioned in the qhost file.
# Returns: a dict with job ID keys. Each value holds another dict with the
#   keys: 'h_vmem' and 'maxvmem', for requested and used memory
#   respectively
    qs_file='qstat.xml'
    if not DEBUG:
        import tempfile,subprocess
        tmpfile=tempfile.NamedTemporaryFile()
        subprocess.call(['qstat','-u','*','-j','*','-xml'],stdout=tmpfile)
        qs_file=tmpfile.name
    qs = ET.parse(qs_file)
    qstat = {}
    for element in qs.getroot().iter('element'):
        jobstat={}
        # record the job ID, if it exists. If not, skip it
        key=element.find('JB_job_number')
        if key is None:
            continue
        jid=key.text
        # record the requested memory (h_vmem)
        for qreq in element.iter('qstat_l_requests'):
            key=qreq.find('CE_name')
            if key.text == 'h_vmem':
                jobstat[key.text]=qreq.find('CE_doubleval').text
        # record current maximum usage (maxvmem)
        for scaled in element.iter('scaled'):
            key=scaled.find('UA_name')
            if key.text == 'maxvmem' or key.text == 'io':
                jobstat[key.text]=scaled.find('UA_value').text
        qstat[jid]=jobstat
    return qstat

def convert_mem(string):
# Convert strings like 10G and 200M to bytes. Also converts "-" to 0.
    num=0.0
    if 'G' in string:
        fixed_str=string.replace("G","")
        num=float(fixed_str)*10**(11)
    else:
        if 'M' in string:
            fixed_str=string.replace("M","")
            num=float(fixed_str)*10**(8)
    if num!=0.0 or string=='-':
        return num
    return string

def get_gigs(string):
# Also too lazy to remember what to divide by to convert bytes back into gigs
    return float(string)/10**11

def collect_stats(ele, qstat,queue):
# for a node in the queue that matches the requested queue, pull out interesting things 
# also cross-reference the jobs that we pulled out of qstat in that handy dict we made
# to come up with total requested, used, and available resources on a particular node
# for this queue
# Returns: a dict with the keys:host, mem_used, mem_total, num_proc, load_avg, h_vmem, and maxvmem
    hostvalues=['mem_used', 'mem_total', 'num_proc', 'load_avg']
    jobvalues=[]

    row={}
    row['host']=ele.attrib['name']
    # pretty sure these all exist
    for hostvalue in ele.iter('hostvalue'):
        if hostvalue.attrib['name'] in hostvalues:
            row[hostvalue.attrib['name']]=convert_mem(hostvalue.text)
    req=0.0
    used=0.0
    for job in ele.findall('job'):
        jid=job.attrib['name']
        #skip jobs not belonging to current queue
        for jobvalue in job.findall('jobvalue'):
            if jobvalue.attrib['name']=='qinstance_name' and not queue in jobvalue.text:
                continue

        for jv in job.iter('jobvalue'):
            if jv.attrib['name'] in jobvalues:
                row[jv.attrib['name']]=jv.text
        if jid in qstat:
            mem=qstat[jid]
            if 'h_vmem' in mem:
                req+=float(mem['h_vmem'])
            if 'maxvmem' in mem:
                used+=float(mem['maxvmem'])
    row['h_vmem']=req
    row['maxvmem']=used
    qhost_use=0
    qstat_use=0
    row['qhost_use']=safe_div(float(row['maxvmem']), float(row['h_vmem']))
    row['qstat_use']=safe_div(float(row['mem_used']), float(row['mem_total']))
    return row



# Parse the args and call main
import sys
import argparse
parser = argparse.ArgumentParser(description='Calculate current queue usage')
parser.add_argument('queue', help='the queue to calculate for', default='production')
parser.add_argument('--debug', action='store_true')
parser.add_argument('--pretty', action='store_true', help='print human-friendly table')
parser.add_argument('--prometheus', help='send metrics to given prometheus pushgateway')
args=parser.parse_args()
DEBUG=args.debug
main(args.queue, args.pretty, args.prometheus)
