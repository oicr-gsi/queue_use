from setuptools import setup

setup(
    name='queue_use',
    version='0.2',
    packages=[],
    scripts=['queue_use'],
    license='MIT',
    long_description='Convert SGE queue information into Prometheus format',
    install_requires=['prometheus_client >= 0.6.0']
)
