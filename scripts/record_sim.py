import os
import subprocess
import sys
import time
import argparse
from datetime import datetime

def record_simulation(target_script, output_dir="outputs/videos", record_time=20, resolution="1920x1080", camera_pos="[2.0, 0.0, 1.0]"):
    """
    Records a simulation run using Xvfb and FFmpeg.
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_name = os.path.basename(target_script).replace(".py", "")
    output_file = os.path.join(output_dir, f"{script_name}_{timestamp}.mp4")
    
    display_num = "99"
    xvfb_res = f"{resolution}x24"
    
    # Setup environment (only DISPLAY is required, inherit everything else)
    env = os.environ.copy()
    env["DISPLAY"] = f":{display_num}"
    
    print(f"--- Starting Xvfb on display :{display_num} at {resolution} ---")
    xvfb_proc = subprocess.Popen([
        "Xvfb", f":{display_num}", "-screen", "0", xvfb_res, "-ac"
    ])
    time.sleep(2)
    
    try:
        print(f"--- Starting Simulation: {target_script} ---")
        # Build command dynamically
        cmd = [
            sys.executable, 
            target_script, 
            "env.viewer=gl", 
            "env.num_frames=300",
            f"env.width={resolution.split('x')[0]}",
            f"env.height={resolution.split('x')[1]}",
            f"env.camera_pos={camera_pos}"
        ]
        
        sim_proc = subprocess.Popen(cmd, env=env)
        
        # Warmup delay to avoid black frames during JIT compilation
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
    parser = argparse.ArgumentParser(description="Headless simulation recording tool.")
    parser.add_argument("script", nargs="?", default="experiments/demo.py", 
                        help="Path to the simulation script to run (default: experiments/demo.py)")
    parser.add_argument("--output", default="outputs/videos", help="Output directory")
    parser.add_argument("--time", type=int, default=20, help="Recording duration in seconds")
    parser.add_argument("--res", default="1920x1080", help="Video resolution (WxH)")
    parser.add_argument("--camera", default="[2.0, 0.0, 1.0]", help="Camera position in Hydra format")
    
    args = parser.parse_args()
    
    # Ensure script exists
    if not os.path.exists(args.script):
        print(f"Error: Script not found at {args.script}")
        sys.exit(1)
        
    record_simulation(args.script, args.output, args.time, args.res, args.camera)
