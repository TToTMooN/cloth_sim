import os
import subprocess
import time
from datetime import datetime

def record_simulation(output_dir="outputs/videos", record_time=20, resolution="1920x1080"):
    """
    Records a simulation run using Xvfb and FFmpeg with optimized framing/resolution.
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"sim_{timestamp}.mp4")
    
    display_num = "99"
    xvfb_res = f"{resolution}x24"
    
    # Internal CUDA paths for Blackwell (RTX 5090)
    internal_cuda = "/home/lingfeng/playground/cloth_sim/.venv/lib/python3.11/site-packages/nvidia/cu13"
    
    env = os.environ.copy()
    env["DISPLAY"] = f":{display_num}"
    env["CUDA_HOME"] = internal_cuda
    env["PATH"] = f"{internal_cuda}/bin:{env.get('PATH', '')}"
    env["LD_LIBRARY_PATH"] = f"{internal_cuda}/lib:{env.get('LD_LIBRARY_PATH', '')}"
    env["TORCH_CUDA_ARCH_LIST"] = "12.0"
    
    print(f"--- Starting Xvfb on display :{display_num} at {resolution} ---")
    xvfb_proc = subprocess.Popen([
        "Xvfb", f":{display_num}", "-screen", "0", xvfb_res, "-ac"
    ])
    time.sleep(2)
    
    try:
        print("--- Starting Simulation (allowing 12s for JIT/warmup) ---")
        # Pass resolution and camera zoom out via Hydra
        sim_proc = subprocess.Popen([
            "/home/lingfeng/playground/cloth_sim/.venv/bin/python", 
            "experiments/demo.py", 
            "env.viewer=gl", 
            "env.num_frames=300",
            f"env.width={resolution.split('x')[0]}",
            f"env.height={resolution.split('x')[1]}",
            "env.camera_pos=[2.0, 0.0, 1.0]"
        ], env=env)
        
        # Warmup delay to avoid black frames during compilation
        time.sleep(12)
        
        print(f"--- Starting FFmpeg recording to {output_file} ---")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "x11grab", 
            "-video_size", resolution, 
            "-i", f":{display_num}", 
            "-t", str(record_time), 
            "-pix_fmt", "yuv420p", 
            output_file
        ]
        
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"--- Recording Complete: {output_file} ---")
        
    finally:
        print("--- Cleaning up processes ---")
        if 'sim_proc' in locals():
            sim_proc.terminate()
        xvfb_proc.terminate()
        xvfb_proc.wait()

if __name__ == "__main__":
    record_simulation()
