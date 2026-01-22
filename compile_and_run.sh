cd build
rm -rf *
cmake ..
make
cd ..
python3 recup_data.py
