import os
SERVICE_VERSION='vision-1.0'
HOST=os.getenv('VISION_HOST','0.0.0.0')
PORT=int(os.getenv('VISION_PORT','8084'))
MAX_PIXELS=int(os.getenv('VISION_MAX_PIXELS','16000000'))
THERMAL_TOLERANCE=float(os.getenv('VISION_THERMAL_TOLERANCE_C','4'))
GAUGE_TOLERANCE=float(os.getenv('VISION_GAUGE_TOLERANCE_PSI','6'))
LOG_LEVEL=os.getenv('VISION_LOG_LEVEL','info')
LLAMA_URL=os.getenv('VISION_LLAMA_URL','') # reserved; intentionally unused
CACHE_SIZE=int(os.getenv('VISION_CACHE_SIZE','64'))
