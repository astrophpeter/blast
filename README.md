# blast
Django web app for the automatic characterization of supernova hosts

## Running locally
1. Install the [Docker desktop app](https://www.docker.com/products/docker-desktop)
2. Open up the command line and pull the Docker image of the lastest commit on main:

`$ docker pull ghcr.io/astrophpeter/blast:edge`

3. Run the image a make blast visible to your machine on port 8000:

`$ docker run --publish 8000:8000 image_ID`

where you can find image_ID in the Docker Desktop app or by running `$ docker images`

4. Got to [localhost:8000/host/](localhost:8000/host/) in your browser

