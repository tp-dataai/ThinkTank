import json
from minio import Minio

from thinktank.config.config import MinioConfig

minio_client = None
def get_minio_client():
    global minio_client

    if minio_client is None:
        # 创建 MinIO 客户端的内容；
        minio_client = Minio(
            endpoint=MinioConfig.minio_endpoint,
            access_key=MinioConfig.minio_access_key,
            secret_key=MinioConfig.minio_secret_key,
            secure=False  # 控制使用 http 还是 https 来进行数据传输。
        )

        #====================================================================
        # todo 问题1：企业开发中是否会在代码中来创建桶的内容？？
        # 先获取桶，然后再判断桶是否存在，不存在就新创建

        bucket_name = MinioConfig.minio_bucket_name
        if not minio_client.bucket_exists(bucket_name):   # type:ignore
            minio_client.make_bucket(bucket_name)         # type:ignore

        # 完成桶的创建后还需要 配置桶的权限
        policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                        "Resource": f"arn:aws:s3:::{bucket_name}",
                    },
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    },
                ],
            }
        minio_client.set_bucket_policy(bucket_name, policy=json.dumps(policy))
        #========================================================================
    
    return minio_client