#!/usr/bin/env bash

PREFIX=$(cd "$(dirname "$0")"; pwd)
cd $PREFIX

source ~/.bashrc

python -u proxy_check.py
date
