from setuptools import setup, find_packages

setup(
    name='vckb',
    version='1.0.0',
    description='VC-Keyboard Python SDK — USB CDC Serial driver for ESP32-S3 peripheral board',
    packages=find_packages(),
    install_requires=['pyserial>=3.5'],
    python_requires='>=3.8',
)
