apis:
	cd $(dirname $0)
	git clone https://github.com/hu-tao-supremacy/api.git apis
	python3 sym.py

participant:
	cd $(dirname $0)
	git clone https://github.com/hu-tao-supremacy/api.git apis
	cd apis && git checkout boom/participant

