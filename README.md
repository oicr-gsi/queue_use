# SGE Usage Calculator

Calculate the usage of a Sun Grid Engine / Open Grid Engine queue using h_vmem and maxvmem from qhost and qstat.

## Requirements

* Python 2.7
* The script depends on a system call out to qstat and qhost

## Usage

```
usage: queue_use.py [-h] [--debug] queue

Calculate current queue usage

positional arguments:
  queue       the queue to calculate for

optional arguments:
  -h, --help  show this help message and exit
  --debug
```

## Output format

Output goes to standard out, tab-separated with a header:

* Node Size (G): the size of each node in gigabytes (or "Total" for a sum of all nodes)
* Busy-ness (%): How much memory has been requested or reserved as a percentage of the total amount of memory available (0-100)
* Requested (G): the total amount of memory requested for nodes of this size
* Total (G) : the total amount of memory available for nodes of this size
* Used (G) : the total amount of memory being used on nodes of this size
* Efficiency (%) : the amount of memory being used as a percentage of the total amount of requested memory

## License

[MIT License](LICENSE) Ontario Institute for Cancer Research

## Contact

Contact the developers on Github Issues: https://github.com/oicr-gsi/sge_usage/issues
