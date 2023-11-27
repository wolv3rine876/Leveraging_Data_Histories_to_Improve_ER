#! /bin/bash

# This script installs the necessary packages using apt.

apt update;

echo "========= 7zip ========";
apt install -y p7zip-full;

echo "========= GNU parallel ========";
apt install -y parallel;
