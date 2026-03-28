"""
检查并重建向量嵌入
"""
import asyncio
from app.services.api_retrieval_service import get_api_retrieval_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """检查并重建向量嵌入"""
    logger.info("=" * 60)
    logger.info("检查向量嵌入状态")
    logger.info("=" * 60)

    retrieval_service = get_api_retrieval_service()

    # 检查集合是否存在以及点数量
    try:
        collection_info = await retrieval_service.vector_store.client.get_collection(
            collection_name="api_embeddings"
        )
        point_count = collection_info.points_count
        logger.info(f"✓ Qdrant集合存在，当前点数量: {point_count}")

        if point_count == 0:
            logger.warning("⚠ 向量嵌入为空，需要重建")
            logger.info("开始重建向量嵌入...")
            await retrieval_service.rebuild_all_embeddings()
            logger.info("✓ 向量嵌入重建完成")

            # 再次检查
            collection_info = await retrieval_service.vector_store.client.get_collection(
                collection_name="api_embeddings"
            )
            new_count = collection_info.points_count
            logger.info(f"✓ 重建后点数量: {new_count}")
        else:
            logger.info("✓ 向量嵌入已存在，无需重建")

    except Exception as e:
        logger.error(f"❌ 检查失败: {e}", exc_info=True)
        logger.info("尝试重建向量嵌入...")
        try:
            await retrieval_service.rebuild_all_embeddings()
            logger.info("✓ 向量嵌入重建完成")
        except Exception as rebuild_error:
            logger.error(f"❌ 重建失败: {rebuild_error}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
