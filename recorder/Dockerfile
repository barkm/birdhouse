FROM google/cloud-sdk:slim
RUN apt-get update && apt-get install -y ffmpeg
COPY record.sh .
COPY upload.sh .
CMD ./upload.sh $(./record.sh $STREAM_URL)
