# Remote Development Guide

This guide covers specialized workflows for running and visualizing simulations in headless or remote server environments.

## 1. Remote Visualization

Simulation frames often cannot be streamed directly over standard SSH/X11 connections. Use one of the following methods for remote viewing:

### A. Headless Video Recording
Record simulation sequences to an `.mp4` file for later viewing. This tool can wrap any simulation script:
```bash
# Record default demo
python3 scripts/record_sim.py

# Record a specific experiment
python3 scripts/record_sim.py scripts/my_experiment.py --time 30
```
*Requires `xvfb` and `ffmpeg` installed on the host.*

### B. Interactive WebRTC Streaming
Use the interactive server to see a live stream in your browser:
```bash
python -m interactive_server.app
```

## 2. Specialized Hardware
If your remote server uses **NVIDIA Blackwell (RTX 5090)** GPUs, please see the [Blackwell Setup Guide](BLACKWELL_SETUP.md) for required compiler and PyTorch configurations.
