"""CLI entry point - now delegates to new modular structure"""
import sys
import click
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")


@click.group()
def cli():
    """LLM Wiki Agent CLI - WikiRepo架构(见 ARCHITECTURE.md)"""
    pass


@cli.command()
@click.argument("doc_path")
def ingest(doc_path: str):
    """摄入原始文档到知识库"""
    from src.agent.wiki_agent import WikiAgent

    agent = WikiAgent()
    try:
        result = agent.ingest(doc_path)
        click.echo(f"✅ Ingest 完成: +{result['pages_created']} created, ~{result['pages_updated']} updated")
        for page in result.get("pages", []):
            click.echo(f"   - {page['title']} ({page['type']})")
    except Exception as e:
        click.echo(f"❌ Ingest 失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("question")
@click.option("--user-id", default=None, help="用户 ID")
def query(question: str, user_id: str = None):
    """向知识库提问"""
    from src.agent.wiki_agent import WikiAgent

    agent = WikiAgent()
    try:
        result = agent.query(question, user_id)
        click.echo(f"\n{'='*60}")
        click.echo(f"置信度: {result['confidence']}")
        click.echo(f"\n{result['answer']}")

        if result["wiki_pages"]:
            click.echo(f"\n引用页面:")
            for p in result["wiki_pages"]:
                click.echo(f"   - [[{p['title']}]] ({p['path']})")

        if result["raw_sources"]:
            click.echo(f"\n原始来源:")
            for s in result["raw_sources"]:
                click.echo(f"   - {s['title']} ({s['path']})")
    except Exception as e:
        click.echo(f"❌ Query 失败: {e}", err=True)
        sys.exit(1)


@cli.command()
def lint():
    """检查知识库健康状态"""
    from src.agent.wiki_agent import WikiAgent

    agent = WikiAgent()
    try:
        report = agent.lint()

        if report["orphaned_pages"]:
            click.echo(f"\n🔗 孤立页面（未被引用）:")
            for p in report["orphaned_pages"]:
                click.echo(f"   - {p}")

        if report["broken_links"]:
            click.echo(f"\n❌ 断链:")
            for l in report["broken_links"]:
                click.echo(f"   - {l}")

        if report["contradictions"]:
            click.echo(f"\n⚠️ 矛盾陈述:")
            for c in report["contradictions"]:
                click.echo(f"   - {c}")

        if report["stale_pages"]:
            click.echo(f"\n⏰ 过时内容:")
            for p in report["stale_pages"]:
                click.echo(f"   - {p}")

        if report["suggestions"]:
            click.echo(f"\n💡 优化建议:")
            for s in report["suggestions"]:
                click.echo(f"   - {s}")

        if not any([report["orphaned_pages"], report["broken_links"],
                    report["contradictions"], report["stale_pages"], report["suggestions"]]):
            click.echo("✅ 知识库健康，无明显问题")

    except Exception as e:
        click.echo(f"❌ Lint 失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--space-id", default=None, help="飞书知识空间 ID")
def sync(space_id: str = None):
    """同步飞书知识空间文档"""
    from src.config import settings
    from src.sync import FeishuClient
    from src.agent.wiki_agent import WikiAgent

    if not settings.feishu_app_id or not settings.feishu_app_secret:
        click.echo("❌ 缺少飞书配置: FEISHU_APP_ID / FEISHU_APP_SECRET", err=True)
        sys.exit(1)

    client = FeishuClient(settings.feishu_app_id, settings.feishu_app_secret)
    agent = WikiAgent()

    try:
        space = space_id or client.get_wiki_space_id()
        click.echo(f"📥 同步知识空间: {space}")

        nodes = client.list_wiki_nodes(space)
        click.echo(f"   共 {len(nodes)} 个节点")

        docx_nodes = [n for n in nodes if n.obj_type == "docx"]
        click.echo(f"   其中 {len(docx_nodes)} 个 docx 文档")

        for node in docx_nodes[:10]:
            click.echo(f"   📄 {node.title}...")
            try:
                md_content = client.get_docx_markdown(node.node_token)
                safe_name = f"feishu_{node.node_token[:8]}"
                raw_path = settings.raw_dir / "articles" / f"{safe_name}.md"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(md_content, encoding="utf-8")

                result = agent.ingest(str(raw_path.relative_to(settings.wiki_repo_path)))
                click.echo(f"      ✅ +{result['pages_created']}/~{result['pages_updated']}")
            except Exception as e:
                click.echo(f"      ❌ {e}", err=True)

        click.echo("\n✅ 同步完成")

    except Exception as e:
        click.echo(f"❌ 同步失败: {e}", err=True)
        sys.exit(1)


@cli.command()
def serve():
    """启动 FastAPI 服务"""
    import uvicorn
    from src.api.app import app

    click.echo("🚀 启动 wiki_service API...")
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    cli()