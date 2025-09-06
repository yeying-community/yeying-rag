from minio import Minio
from minio.error import S3Error
from dotenv import load_dotenv
import io
import os

load_dotenv()



def test_minio_connection():
    """测试MinIO连接和基本操作"""

    # MinIO连接配置
    client = Minio(
        os.getenv("DOMAIN"),
        access_key=os.getenv("ACCESS_KEY"),
        secret_key=os.getenv("SECRET_KEY"),
        secure=os.getenv("TLS")
    )

    try:
        print("🔗 正在测试MinIO连接...")

        # 1. 测试连接 - 列出所有存储桶
        buckets = client.list_buckets()
        print("✅ 连接成功！")
        print(f"📦 当前存储桶数量: {len(buckets)}")

        for bucket in buckets:
            print(f"   - {bucket.name} (创建时间: {bucket.creation_date})")

        # 2. 创建测试存储桶
        test_bucket = "test-bucket"
        print(f"\n📁 检查存储桶 '{test_bucket}'...")

        if not client.bucket_exists(test_bucket):
            client.make_bucket(test_bucket)
            print(f"✅ 存储桶 '{test_bucket}' 创建成功")
        else:
            print(f"ℹ️  存储桶 '{test_bucket}' 已存在")

        # 3. 上传测试文件
        print(f"\n📤 上传测试文件...")
        test_content = "Hello MinIO! 这是一个测试文件。"
        test_file = io.BytesIO(test_content.encode('utf-8'))

        client.put_object(
            test_bucket,
            "test.txt",
            test_file,
            length=len(test_content.encode('utf-8')),
            content_type="text/plain"
        )
        print("✅ 文件上传成功")

        # 4. 下载测试文件
        print(f"\n📥 下载测试文件...")
        response = client.get_object(test_bucket, "test.txt")
        downloaded_content = response.read().decode('utf-8')
        print(f"✅ 文件下载成功")
        print(f"📄 文件内容: {downloaded_content}")

        # 5. 列出存储桶中的对象
        print(f"\n📋 列出存储桶 '{test_bucket}' 中的对象:")
        objects = client.list_objects(test_bucket)
        for obj in objects:
            print(f"   - {obj.object_name} (大小: {obj.size} bytes)")

        # 6. 生成预签名URL（用于分享文件）
        from datetime import timedelta
        presigned_url = client.presigned_get_object(test_bucket, "test.txt", expires=timedelta(hours=1))
        print(f"\n🔗 预签名URL (1小时有效): {presigned_url}")

        print(f"\n🎉 所有测试完成！MinIO工作正常。")

    except S3Error as e:
        print(f"❌ MinIO错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False
    finally:
        # 清理资源
        if 'response' in locals():
            response.close()

    return True

if __name__ == "__main__":
    print("MinIO Python SDK 测试")
    print("=" * 50)

    # 检查MinIO库版本
    try:
        import minio
        print(f"📚 MinIO SDK版本: {minio.__version__}")
    except AttributeError:
        print("📚 MinIO SDK已安装")

    print()

    # 运行测试
    success = test_minio_connection()

    if success:
        print("\n✅ 测试成功！你可以开始使用MinIO了。")
    else:
        print("\n❌ 测试失败，请检查配置。")