#!/usr/bin/env python

import xml.etree.ElementTree as ET
import os

DEBUG=0

# What do I want?
# How busy the queue is as a whole (requested h_vmem/total available mem)
# How busy particular machine sizes are (16G, 24G, 125.1, 252.3, 220.8)
# how hoggy our processes are being (requested vs actual)

def main(queue):
	qstat=parse_qstat()
	if DEBUG:
		print "Loading qhosts.xml file (using file in cwd)"
	else:
		os.system(" ".join(["qhost","-xml","-q","-j","-F",">qhosts.xml"]))
	qh = ET.parse('qhosts.xml')

	table=[]
	machine_size={}
	total_hvmem=0
	total_memtotal=0
	total_maxvmem=0
	for host in qh.getroot():
		for q in host.iter('queue'):
			if q.attrib['name'] == queue:
				row=collect_stats(host, qstat)
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
				table.append(row)

	print queue
	print "Node Size (G)\tBusy-ness (%)\tRequested (G)\tTotal (G)\tUsed (G)\tEfficiency (%)"
	for size in machine_size:
		sizerow=machine_size[size]
		print "%s\t%.2f\t%.2f\t%.2f\t%.2f" % ( get_gigs(size),(100.0*safe_div(sizerow['h_vmem'],sizerow['mem_total'])),get_gigs(sizerow['h_vmem']), get_gigs(sizerow['mem_total']), (100.0*safe_div(sizerow['maxvmem'], sizerow['h_vmem'])) )

	print "Total\t%.2f\t%.2f\t%.2f\t%.2f" % ( (100.0*safe_div(total_hvmem,total_memtotal)),get_gigs(total_hvmem),get_gigs(total_memtotal),(100.0*safe_div(total_maxvmem,total_hvmem)) )


def safe_div(num, denom):
# Because I'm too lazy to check for a 0 denominator every time I divide
	if denom != 0:
		return num/denom
	else:
		return 0

def parse_qstat():
# Parsing the qstat XML log because I don't want to have to iterate
# through the file for every job mentioned in the qhost file.
# Returns: a dict with job ID keys. Each value holds another dict with the
# 	keys: 'h_vmem' and 'maxvmem', for requested and used memory
#	respectively
	if DEBUG:
		print "Parsing qstat.xml file (using file in cwd)"
	else:
		os.system(" ".join(["qstat","-u \*","-q", queue, "-j \*","-xml", ">qstat.xml"]))
	qs = ET.parse('qstat.xml')
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

def collect_stats(ele, qstat):
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
args=parser.parse_args()
DEBUG=args.debug
main(args.queue)
