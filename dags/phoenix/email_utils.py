"""
邮件发送与报警工具模块

本模块提供两类能力：
1) send_topic_card_email：将 Gemini 生成的 Markdown 报告渲染为 HTML 正文并随附件发送；
2) send_alert_email：在出现故障时发送报警通知。

所有账户与收件人配置均通过 Airflow Variables 进行集中管理，并在本地调试时
回退到同名环境变量或空值。建议优先使用应用专用密码（App Password）登录 Gmail。
"""
import os
import os
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, List
import markdown  # 用于将Markdown转换为HTML

# 捕获因在非Airflow环境测试时可能出现的Variable导入失败
try:
    from airflow.models import Variable
except ImportError:
    print("Could not import Airflow Variables. Using dummy values for local testing.")
    class Variable:  # type: ignore
        @staticmethod
        def get(key, default_var=None, deserialize_json=False):
            if deserialize_json:
                return []
            return os.getenv(key.upper(), default_var)

log = logging.getLogger(__name__)

# --- 从Airflow Variables安全地读取邮件配置 ---
GMAIL_USER = Variable.get("gmail_smtp_user")
GMAIL_APP_PASSWORD = Variable.get("gmail_smtp_password")

# 业务报告收件人（新的变量名）
BUSINESS_RECIPIENTS = Variable.get("business_report_email_list", default_var=None, deserialize_json=True)
# 报警收件人（新的变量名）
ALERT_RECIPIENTS = Variable.get("system_alert_email_list", default_var=None, deserialize_json=True)

# 兼容性回退（如新变量未设置，则回退到旧变量）
if not BUSINESS_RECIPIENTS:
    BUSINESS_RECIPIENTS = Variable.get("recipient_email_list", default_var=None, deserialize_json=True)
if not ALERT_RECIPIENTS:
    ALERT_RECIPIENTS = Variable.get("alert_email_list", default_var=None, deserialize_json=True)


def send_topic_card_email(report_files: list[str], execution_date_str: str):
    """
    发送包含选题卡片报告的邮件。

    Args:
        report_files (list[str]): 一个或多个 Markdown 报告文件的绝对路径列表。
        execution_date_str (str): DAG 的执行日期字符串 (YYYY-MM-DD)，用于邮件主题。

    Returns:
        None: 发送成功返回 None；若失败会记录日志并抛出异常。
    """
    if not report_files:
        log.warning("No report files found to send. Skipping email task.")
        return

    if not BUSINESS_RECIPIENTS:
        log.error("Business recipient email list is empty. Aborting email task.")
        return

    log.info(f"Preparing to send email with {len(report_files)} report(s) to: {BUSINESS_RECIPIENTS}")

    # 合并所有报告内容用于邮件正文
    combined_md_content = ""
    for file_path_str in report_files:
        p = Path(file_path_str)
        if p.exists():
            # 在每个文件内容前添加一个标题，以区分多个报告
            combined_md_content += f"# Report: {p.name}\n\n"
            combined_md_content += p.read_text(encoding="utf-8") + "\n\n---\n\n"
        else:
            log.warning(f"Report file not found during email preparation: {p}")

    if not combined_md_content:
        log.error("All specified report files were empty or could not be read. Aborting email.")
        return

    # 使用 markdown 库将完整的 Markdown 文本转换为 HTML
    # 启用 nl2br 扩展，将单换行自动转为 <br>，避免客户端把软换行合并为一行
    html_content = markdown.markdown(
        combined_md_content,
        extensions=['fenced_code', 'tables', 'nl2br'],
        output_format='html5'
    )

    # 构建邮件主题
    subject = f"【每日选题简报】 - {execution_date_str}"

    # 创建 EmailMessage 对象
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = ", ".join(BUSINESS_RECIPIENTS)

    # 设置邮件正文，优先使用 HTML 格式
    msg.set_content("This is an automated report. Please view it in an HTML-compatible email client.")
    msg.add_alternative(html_content, subtype='html')

    # 添加所有报告文件作为附件
    for file_path_str in report_files:
        p = Path(file_path_str)
        if p.exists():
            with open(p, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="text",
                    subtype="markdown",  # 或者 'plain'
                    filename=p.name
                )

    # 连接到 Gmail SMTP 服务器并发送邮件
    log.info(f"Connecting to smtp.gmail.com:465 to send email...")
    try:
        # 使用 SMTP_SSL 实现 SSL 加密连接
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        log.info("✅ Email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        log.error("SMTP Authentication Error: Check your GMAIL_USER and GMAIL_APP_PASSWORD. Ensure 'Less secure app access' is configured if not using an App Password.")
        raise
    except Exception as e:
        log.error(f"❌ Failed to send email via SMTP: {e}")
        raise



def send_alert_email(subject: str, body: str, recipients: Optional[List[str]] = None):
    """
    发送报警通知邮件（纯文本 + 简单HTML）。

    参数优先级：
    1) 显式传入 recipients；
    2) 使用 Airflow Variable: system_alert_email_list；
    3) 回退 alert_email_list 或 recipient_email_list（兼容旧配置）。

    Args:
        subject (str): 邮件主题。
        body (str): 邮件正文（纯文本，将自动转换出简单 HTML 版本）。
        recipients (Optional[List[str]]): 收件人列表；为空时走变量与回退逻辑。

    Returns:
        None: 发送成功返回 None；异常时仅记录日志并吞掉异常，避免二次失败。
    """
    try:
        alert_list = recipients
        if not alert_list:
            alert_list = ALERT_RECIPIENTS
        if not alert_list:
            # 兼容旧配置
            alert_list = Variable.get("alert_email_list", default_var=None, deserialize_json=True)
        if not alert_list:
            # 最后回退到业务收件人
            alert_list = BUSINESS_RECIPIENTS

        if not alert_list:
            log.error("Alert email list is empty. Skipping alert email.")
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = ", ".join(alert_list)

        # 文本 + 简单HTML
        msg.set_content(body)
        html_body = markdown.markdown(body.replace("\n", "\n\n"))
        msg.add_alternative(html_body, subtype='html')

        log.info(f"Sending alert email to: {alert_list}")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        log.info("✅ Alert email sent successfully!")
    except Exception as e:
        log.error(f"❌ Failed to send alert email: {e}")
        # 报警失败不再向上抛出，避免二次失败
        return

