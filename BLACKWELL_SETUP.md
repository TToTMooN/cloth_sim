# NVIDIA Blackwell (RTX 5090) Setup Guide

This guide documents the specialized environment configuration required for **NVIDIA Blackwell (sm_120)** architecture GPUs.

## 1. PyTorch Nightly (CUDA 13.0)
Standard stable versions may lack Blackwell kernels. Always use the nightly build with CUDA 13.0:
```bash
uv pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130 --upgrade
```

## 2. Internal CUDA Toolkit
To ensure compiler compatibility with PyTorch's CUDA version (13.0), we use an internal toolkit:
```bash
uv pip install nvidia-cuda-nvcc
```
The compiler components will be located within your virtual environment: `.venv/lib/python3.11/site-packages/nvidia/cu13`.

## 3. cuRobo & Extension Compilation
`cuRobo` is included as a submodule. Ensure it is initialized before compiling:
```bash
git submodule update --init --recursive
```

When building `cuRobo` or other CUDA-dependent packages, set the following environment variables to target the RTX 5090 and use the internal compiler:

```bash
# Target Compute Capability 12.0
export TORCH_CUDA_ARCH_LIST="12.0"

# Point to internal toolkit
export CUDA_HOME=$(find .venv -name cu13 -type d)
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib:$LD_LIBRARY_PATH"
```

## 4. Troubleshooting
- **"No kernel image available"**: This usually means the code was compiled without `sm_120` support. Re-install the problematic package with `TORCH_CUDA_ARCH_LIST="12.0"`.
- **Compiler Mismatch**: Ensure you are not using the system `/usr/bin/nvcc`. Check `which nvcc` points to your `.venv` path.
