# Remote Development Guide (RTX 5090 / Blackwell)

This guide documents the setup and workflows for developing on this repository remotely, specifically targeting the **NVIDIA Blackwell (RTX 5090)** architecture.

## 1. SSH Access

A new Ed25519 SSH key has been generated for this environment.

- **Key Label**: `lingfengsun@berkeley.edu`
- **Identity File**: `~/.ssh/id_ed25519`
- **Verification**: Run `ssh -T git@github.com` to confirm GitHub connectivity.

## 2. Blackwell GPU Optimization (sm_120)

The RTX 5090 requires specialized kernels (Compute Capability 12.0).

### PyTorch Nightly
We use PyTorch Nightlies built for CUDA 13.0 to support the Blackwell architecture.
```bash
uv pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130 --upgrade
```

### Internal CUDA Toolkit
To avoid system-wide CUDA mismatches, we use an internal toolkit installed via `uv`:
```bash
uv pip install nvidia-cuda-nvcc
```
The toolkit is located in: `.venv/lib/python3.11/site-packages/nvidia/cu13`.

### cuRobo Compilation
When building `cuRobo` or other CUDA extensions, ensure the following environment variables are set:
```bash
export TORCH_CUDA_ARCH_LIST="12.0"
export CUDA_HOME=$(find .venv -name cu13 -type d)
```

## 3. Remote Visualization

Since X11 windows cannot be streamed directly over most SSH connections without performance loss, we support two remote visualization modes:

### A. Headless Video Recording
Use the Python utility to record simulations to an `.mp4` file.
```bash
python -m sim.utils.record_video
```
*Requires `xvfb` and `ffmpeg` installed on the host system.*

### B. Interactive WebRTC Streaming
For live interaction, use the experimental interactive server (as introduced in PR #1).
```bash
# Start the interactive server
python -m interactive_server.app
```
Then visit the WebRTC frontend to see a live stream of the simulation frames.

## 4. Troubleshooting

- **"No kernel image" error**: Ensure `TORCH_CUDA_ARCH_LIST="12.0"` was set during the installation of `curobo`.
- **"CUDA Mismatch" error**: Ensure you are using the `nvcc` from the internal `.venv` toolkit, not the system `/usr/bin/nvcc`.
