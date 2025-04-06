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

Then, to run:
```bash
python main.py
```