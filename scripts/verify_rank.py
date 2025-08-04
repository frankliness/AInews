import pandas as pd
from eventregistry import *
import os

# --- 请在这里填入您的 API Key ---
EVENTREGISTRY_API_KEY = "b03b250a-97ec-4dd0-905e-a038eb1a73e5"
# -----------------------------------

# csv 文件的路径
CSV_FILE_PATH = 'raw_events (2).csv'

def verify_importance_rank():
    """
    读取 CSV 文件，获取最新10篇文章的 URL，
    并从 EventRegistry API 查询它们的 source importanceRank。
    """
    if not os.path.exists(CSV_FILE_PATH):
        print(f"错误: 找不到文件 '{CSV_FILE_PATH}'。请确保文件与脚本在同一目录下。")
        return

    if EVENTREGISTRY_API_KEY == "YOUR_API_KEY_HERE" or not EVENTREGISTRY_API_KEY:
        print("错误: 请在脚本中填入您的 EventRegistry API Key。")
        return

    try:
        # 1. 读取 CSV 并获取最新的10条记录
        df = pd.read_csv(CSV_FILE_PATH)
        df['published_at'] = pd.to_datetime(df['published_at'])
        latest_articles_df = df.nlargest(10, 'published_at')
        article_urls = latest_articles_df['url'].tolist()

        print(f"成功读取 {len(article_urls)} 条最新的文章 URL 用于验证...")
        print("-" * 30)

        # 2. 初始化 EventRegistry 客户端
        er = EventRegistry(apiKey=EVENTREGISTRY_API_KEY)

        # 3. 使用 ArticleMapper 将 URLs 转换为 ER 内部的 URIs
        print("正在将文章 URL 映射为 EventRegistry URIs...")
        article_mapper = ArticleMapper(er)
        article_uris = []
        for url in article_urls:
            try:
                uri = article_mapper.getArticleUri(url)
                if uri:
                    article_uris.append(uri)
            except Exception as map_error:
                print(f"  -> 映射 URL 失败: {url}, 错误: {map_error}")
        
        if not article_uris:
            print("\n错误: 无法将任何 URL 映射为有效的 URI。可能是文章已过期或 URL 格式问题。")
            return
            
        print(f"成功映射 {len(article_uris)} 个 URIs。")
        print("-" * 30)

        # 4. 使用获取到的 URIs 进行查询
        q = QueryArticle.queryByUri(article_uris)

        # 5. 定义并“绑定”我们需要返回的额外信息 (这是关键的修正!)
        return_info = ReturnInfo(sourceInfo=SourceInfoFlags(ranking=True))
        q.setRequestedResult(RequestArticleInfo(returnInfo=return_info))

        # 6. 执行查询 (现在 execQuery 不再需要 returnInfo 参数了)
        results = er.execQuery(q)

        # 返回结果是一个字典，key 是 uri, value 是文章详情
        if results and isinstance(results, dict):
            print("查询成功！正在打印 'importanceRank':\n")
            for uri, article_details in results.items():
                article = article_details.get('info', {})
                if not article:
                    continue

                title = article.get('title', 'N/A')
                source_uri = article.get('source', {}).get('uri', 'N/A')
                importance_rank = None

                if 'source' in article and article['source'] and 'ranking' in article['source'] and article['source']['ranking']:
                    importance_rank = article['source']['ranking'].get('importanceRank')

                print(f"文章: {title[:50]}...")
                print(f"  -> 信源 URI: {source_uri}")
                print(f"  -> Importance Rank: {importance_rank}\n")
        else:
            print("查询 API 失败或未返回任何文章。请检查您的 API Key 和网络连接。")
            print("API 原始返回:", results)

    except Exception as e:
        print(f"脚本运行出错: {e}")

if __name__ == "__main__":
    verify_importance_rank()