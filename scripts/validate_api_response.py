#!/usr/bin/env python3
"""
独立的API验证脚本
用于验证eventregistry API返回的数据结构
"""

import eventregistry
import json
import os
from typing import Dict, Any

def main():
    # 1. 从环境变量获取API密钥
    api_key = os.getenv('EVENTREGISTRY_APIKEY')
    if not api_key:
        raise ValueError("环境变量 EVENTREGISTRY_APIKEY 未设置")
    
    print("✅ API密钥已获取")
    
    # 2. 实例化EventRegistry客户端
    er = eventregistry.EventRegistry(api_key)
    print("✅ EventRegistry客户端已初始化")
    
    # 3. 构建查询参数
    # 首先，定义我们希望返回的详细信息结构 (这是我们的"备注")
    return_info = eventregistry.ReturnInfo(
        eventInfo=eventregistry.EventInfoFlags(
            concepts=True,
            socialScore=True,
            totalArticleCount=True, # << 修正：在EventInfoFlags中请求事件级别的总文章数
            # 我们将在下一步获取文章时才请求文章的详细来源信息
        ),
        # 在获取事件列表时，我们通常先不获取文章详情，以加快速度
        # 而是获取事件本身的属性，以及其中一两篇代表性文章的URI或标题
        articleInfo=eventregistry.ArticleInfoFlags(
            concepts=True,      # 获取文章的概念
            sourceInfo=True     # 获取文章的来源信息
        )
    )
    
    # 【核心修复】然后，将这个"备注"放入一个正确的"主订单"中
    # QueryEventsIter 需要的是 RequestEvents 类型的对象
    requested_result = eventregistry.RequestEventsInfo(
        page=1,
        count=10, # 获取最近的10个事件
        sortBy="size", # 按事件规模排序
        returnInfo=return_info # 将我们的详细要求作为参数传入
    )
    
    print("✅ 查询参数已修正并配置")

    # 4. 执行查询
    print("🔄 正在执行API查询...")
    
    # 在这里，我们将修正后的"主订单"传递给服务员
    query = eventregistry.QueryEventsIter(
        categoryUri="news/Politics",
        requestedResult=requested_result
    )

    # 获取第一个事件用于验证
    # q.execQuery(er) 返回的是一个迭代器，我们需要从中获取结果
    events = []
    for event in query.execQuery(er, maxItems=1):
        events.append(event)
    
    if not events:
        print("❌ 未找到任何事件")
        return
    
    event = events[0]
    print(f"✅ 成功获取事件: {event.get('uri', 'N/A')}")
    
    # 5. 从事件中提取第一篇文章
    # 注意：根据新的查询方式，文章列表可能直接在事件对象中
    articles = event.get('articles', {}).get('results', [])
    if not articles:
        # 如果事件对象中没有文章，可能是因为我们需要单独再查一次
        print("ℹ️ 事件对象中未直接包含文章，这是正常现象。我们已获取到事件本身。")
        # 打印事件对象本身的信息进行验证
        print(json.dumps(event, indent=2, ensure_ascii=False))
        # 在这个验证脚本中，我们主要关心事件级别的数据，所以到此即可
        article_to_print = event # 我们可以打印事件本身作为验证
    else:
        article_to_print = articles[0]
        print(f"✅ 成功提取文章: {article_to_print.get('uri', 'N/A')}")

    # 6. 将完整的对象JSON写入文件
    output_filename = "api_response.json"
    print("\n" + "="*80)
    print(f"📋 正在将完整的事件/文章对象JSON写入到文件: {output_filename}")
    print("="*80)
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            # 使用 json.dump 将对象直接写入文件，并保持格式美观
            json.dump(article_to_print, f, indent=2, ensure_ascii=False)
        print(f"✅ 成功！请在脚本同目录下查看 '{output_filename}' 文件。")
    except Exception as e:
        print(f"❌ 写入文件时发生错误: {e}")
    
    print("\n" + "="*80)
    print("📊 事件级别的关键字段:")
    print("="*80)
    
    # 打印事件级别的关键信息
    event_summary = {
        'uri': event.get('uri'),
        'totalArticleCount': event.get('totalArticleCount'),
        'concepts': event.get('concepts'),
        'sourceInfo': event.get('sourceInfo')
    }
    print(json.dumps(event_summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")
        import traceback
        traceback.print_exc() 