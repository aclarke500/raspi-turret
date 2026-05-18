# raspi-turret

This is the code for targeting people and shooting them using the turret me and my team are creating.

This is very much a WIP. Currently using a webcam for dev purposes, planning to use PiCam later on.

I'd recommend using a venv but to each their own.

First, you will need to to install tflite and other dependencies, run:
```bash
pip install tflite-runtime numpy<2 Pillow
mkdir -p ~/tflite_models && cd ~/tflite_models

# Download SSD MobileNet model
wget https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
unzip coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip

# (Optional, if wget fails — create manually instead)
nano coco_labels.txt  # paste in labels from the model's label map it should go in the tflite_models dir you made
```
Use the coco labels in this project. To take photos using a webcam, we use:
```bash
sudo apt install fswebcam
```

And, for good measure:
```bash
pip install -r requirements.txt
```

Pi CSI camera bench test (on the Pi, after `sudo apt install -y python3-picamera2`):
```bash
python hardware_tests/picam_test.py
```

Then, to run the turret server (patrol + live view on port 8000):
```bash
bash run.sh
```

Open `http://<pi-ip>:8000/` in a browser on the same network for the live stream with detection boxes.

Path for actual project on the raspi:
/home/aclarke500/Desktop/tflite-prac


Creds to login on RDP:
aclarke500
Link500

192.168.86.51
ssh aclarke500@192.168.86.51
192.168.86.51 fdc3:c7c1:a69e:5bb0:a400:e063:f9af:6326 
