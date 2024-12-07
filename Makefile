run:
	@source env/bin/activate; python3 main.py

ignore:
	@source env/bin/activate; python3 ignore.py

requirements:
	@source env/bin/activate; python3 -m pip install -r requirements.txt

