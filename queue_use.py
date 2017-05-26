#!/usr/bin/env python

import xml.etree.ElementTree as ET
import os

DEBUG=0

# What do I want?
# How busy the queue is as a whole (requested h_vmem/total available mem)
# How busy particular machine sizes are (16G, 24G, 125.1, 252.3, 220.8)
# how hoggy our processes are being (requested vs actual)

def main(queue):
	if DEBUG:
		print "Parsing qstat.xml file (using file in cwd)"
	else:
		os.system(" ".join("qstat","-u \*","-q", queue, "-j \*","-xml", ">qstat.xml"))
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
	import pprint;
	for host in qh.getroot():
		for q in host.iter('queue'):
			if q.attrib['name'] == queue:
				row=collect_stats(host, qstat)
				hvmem=row['h_vmem']
				memtotal=row['mem_total']
				slots=memtotal
				total_hvmem+=hvmem
				total_memtotal+=memtotal
				if not slots in machine_size:
					machine_size[slots]={'h_vmem':0, 'mem_total':0}
				machine_size[slots]['h_vmem']+=hvmem
				machine_size[slots]['mem_total']+=memtotal

				table.append(row)
	print queue
	print "Total usage\t%f%%\t%d/%d G" % ((100.0*total_hvmem/total_memtotal),get_gigs(total_hvmem),get_gigs(total_memtotal))
	for size in machine_size:
		sizerow=machine_size[size]
		print "%sG usage\t%f%%\t%d/%d G" % (get_gigs(size),(100.0*sizerow['h_vmem']/sizerow['mem_total']),get_gigs(sizerow['h_vmem']), get_gigs(sizerow['mem_total']))


def parse_qstat():
	# detailed_job_info
	#	> djob_info
	#		> element
	#			> JB_job_number <text>
	#			> JB_hard_resource_list
	#				> qstat_l_requests
	#					> CE_name <text, e.g. h_vmem>
	#					> CE_stringval <text, e.g. 6G>
	#					> CE_doubleval <text, e.g. 6442450944.00000>
	#			> JB_ja_tasks
	#				> ulong_sublist
	#					> JAT_scaled_usage_list
	#						> scaled
	#							> UA_name <text, e.g. maxvmem>
	#							> UA_value <text>
	# BLARG
	qs = ET.parse('qstat.xml')
	qstat = {}
	djobvalues=['']
	for element in qs.getroot().iter('element'):
		jobstat={}
		key=element.find('JB_job_number')
		if key is None:
			continue
		jid=key.text
		for qreq in element.iter('qstat_l_requests'):
			key=qreq.find('CE_name')
			if key.text == 'h_vmem':
				jobstat[key.text]=qreq.find('CE_doubleval').text
		# pull out current usage
		for scaled in element.iter('scaled'):
			key=scaled.find('UA_name')
			if key.text == 'maxvmem' or key.text == 'io':
				jobstat[key.text]=scaled.find('UA_value').text
		qstat[jid]=jobstat
	return qstat







def convert_mem(string):
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
	return float(string)/10**11

def collect_stats(ele, qstat):
	# qhost 
	#	> host name
	# 		> hostvalue name
	#		> resourcevalue name dominance (optional from -F)
	#		> queue name (optional from -q)
	#			> queuevalue qname name
	#		> job name (optional from -j)
	#			> jobvalue jobid name
	
	#Things to pull out
	hostvalues=['mem_used', 'mem_total', 'num_proc', 'load_avg']
	queuevalues=['slots_used', 'slots']
	jobvalues=[]

	row={}
	row['host']=ele.attrib['name']
	# pretty sure these all exist
	for hostvalue in ele.iter('hostvalue'):
		if hostvalue.attrib['name'] in hostvalues:
			row[hostvalue.attrib['name']]=convert_mem(hostvalue.text)
	# probably better exist
	for queue in ele.findall('queue'):
		if queue.attrib['name']=="production":
			for qv in queue.iter('queuevalue'):
				if qv.attrib['name'] in queuevalues:
					row[qv.attrib['name']]=qv.text
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
	slots_use=0
	if row['slots']!=0:
		row['slots_use']=float(row['slots_used'])/float(row['slots'])
	if row['h_vmem']!=0:
		row['qhost_use']=float(row['maxvmem'])/float(row['h_vmem'])
	if row['mem_total']!=0:
		row['qstat_use']=float(row['mem_used'])/float(row['mem_total'])
	return row

import sys
import argparse
parser = argparse.ArgumentParser(description='Calculate current queue usage')
parser.add_argument('queue', help='the queue to calculate for', default='production')
parser.add_argument('--debug', action='store_true')
args=parser.parse_args()
DEBUG=args.debug
main(args.queue)