FROM nvcr.io/nvidia/pytorch:25.03-py3

RUN pip install --no-cache-dir "laya[serve]"
EXPOSE 8000

CMD ["laya-serve"]