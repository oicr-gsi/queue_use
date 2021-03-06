# SGE Queue Usage Calculator

Calculate the usage of a Sun Grid Engine / Open Grid Engine queue using h_vmem and maxvmem from qhost and qstat.

## Requirements

* Python 2.7 with [prometheus_client](https://github.com/prometheus/client_python) installed
* Depends on system calls out to qstat, qhost, and iconv (to remove non utf-8 characters)

## Usage

```
usage: queue_use [-h] [--debug] [--pretty] [--prometheus PROMETHEUS] queue

Calculate current queue usage

positional arguments:
  queue                 the queue to calculate for

optional arguments:
  -h, --help            show this help message and exit
  --debug
  --pretty              print human-friendly table
  --prometheus PROMETHEUS
                        send metrics to given prometheus pushgateway

For more information see: https://github.com/oicr-gsi/queue_use
```

## Testing

Generate your own testing files on your SGE install and then use the --debug
flag. Debug relies on the presence of the files qstat.xml and qhosts.xml in the
current working directory.

```
qstat -u \* -j \* -xml | iconv -c -t 'utf-8' -o qstat.xml 
qhost -xml -q -j -F | iconv -c -t 'utf-8' -o qhosts.xml
```

### Pretty Print 

```
python sge_usage.py --pretty --debug production
```

### Prometheus

To test, start a local [Prometheus Pushgateway](https://github.com/prometheus/pushgateway).

```
# Start the local pushgateway using Docker
docker pull prom/pushgateway
docker run -d -p 9090:9091 prom/pushgateway

# Send stats to the pushgateway
python sge_usage.py --prometheus localhost:9090 --debug production
```

Check http://localhost:9090 to see the metrics appearing.


## Output format

### Pretty Print

Output goes to standard out, tab-separated with a header:

* Node Size (G): the size of each node in gigabytes (or "Total" for a sum of all nodes)
* Requested (G): the total amount of memory requested for nodes of this size
* Used (G) : the total amount of memory being used on nodes of this size
* Total (G) : the total amount of memory available for nodes of this size
* Busy-ness (%): How much memory has been requested or reserved as a percentage of the total amount of memory available (0-100)
* Efficiency (%) : the amount of memory being used as a percentage of the total amount of requested memory

### Prometheus Pushgateway

Three metrics are sent to the Prometheus Pushgateway:

* queue_use_hvmem: The current requested virtual memory (bytes) used on the given queue
* queue_use_maxvmem: The current maximum virtual memory (bytes) used on the given queue
* queue_use_memtotal: The current maximum virtual memory (bytes) available on the given queue

Each has attributes:

* job: queue name
* nodesize: size of the node in GB





## License

[MIT License](LICENSE) Ontario Institute for Cancer Research

## Contact

Contact the developers on Github Issues: https://github.com/oicr-gsi/sge_usage/issues
