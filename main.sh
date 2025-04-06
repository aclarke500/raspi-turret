source venv/bin/activate

echo 'Taking photo...'
bash photo.sh
echo 'Photo captured. Analyzing!'
python detect.py