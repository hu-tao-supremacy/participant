# Participant service for One Pass using gRPC

## Installation

### Step 1: Git clone this repo

```
git clone https://github.com/hu-tao-supremacy/participant
cd participant
```

### Step 2: Install dependencies

```
pip install -r requirements.txt
pip instal psycopg2
make apis
make seed
```

The last 2 commands might ask for permission to remove existing file.

### Step 3: Start Docker container

Open docker-compose.yaml and enter username and password

```
docker-compose -f docker-compose.yaml up -d
```

### Step 4: Create .env.local

```
touch .env.local
```

and enter the following

```
export POSTGRES_HOST=localhost
export POSTGRES_USER= //username
export POSTGRES_PASSWORD= //password
export POSTGRES_DB=hts
export POSTGRES_PORT=5432
export GRPC_HOST=localhost
export GRPC_PORT=50051
```

insert user and password that is used in docker.

### Step 5: Run the application

```
python main.py
```

### Step 6: Install [BloomRPC](https://github.com/uw-labs/bloomrpc) and open it

    4.1 In the top left corner, click 2nd tab icon (document with magnifying glass) and import path of `.../participant/apis/proto`

    4.2 In the top left corner, click add icon (green plus icon) and Import protos of `.../participant/apis/proto/hts/participant/service.proto`

    4.3 Add 0.0.0.0:5001 for server address

    4.4 Choose a message to call on the left sidebar and run
