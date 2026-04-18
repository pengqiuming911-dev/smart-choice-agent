"""Compliance checker for PE knowledge base Q&A"""
import re
import os
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Load .env file
from dotenv import load_dotenv
load_dotenv()


class BlockReason(Enum):
    """Reasons for blocking a query or response"""
    NONE = "none"
    SENSITIVE_KEYWORD = "sensitive_keyword"  # Query contains sensitive keywords
    NON_QUALIFIED_INVESTOR = "non_qualified_investor"  # User not in whitelist
    FORBIDDEN_OUTPUT = "forbidden_output"  # Output contains forbidden words
    DATA_LEAKAGE_RISK = "data_leakage_risk"  # Potential PII or confidential data


# === Sensitive keywords that require qualified investor access ===
# From Step 1 compliance requirements - sensitive financial info
SENSITIVE_KEYWORDS = [
    # Specific fund NAV / net value
    r"净值",
    r"单位净值",
    r"累计净值",
    r"基金净值",
    r"最新净值",

    # Specific returns / performance
    r"收益率",
    r"年化收益率",
    r"历史收益",
    r"投资回报",
    r"业绩表现.*?",

    # Specific financial data
    r"管理费",
    r"托管费",
    r"申购费",
    r"赎回费",
    r"佣金",

    # Customer specific info
    r"客户.*?名单",
    r"投资者.*?信息",
    r"高净值客户",
    r"合格投资者.*?名单",

    # Specific investment amounts
    r"起投金额",
    r"认购金额",
    r"投资金额.*?万",
    r"赎回.*?金额",

    # Unauthorized investment advice
    r"买.*?基金",
    r"推荐.*?基金",
    r"投资.*?建议",
    r"应该.*?买",
]

SENSITIVE_PATTERN = re.compile("|".join(SENSITIVE_KEYWORDS), re.IGNORECASE)


# === Forbidden words that should NEVER appear in output ===
# From Step 1 compliance: no guarantees, no "zero risk", etc.
FORBIDDEN_OUTPUT_WORDS = [
    "保本",
    "保收益",
    "稳赚",
    "零风险",
    "保证收益",
    "一定赚钱",
    "收益率.*?保证",
    "投资.*?保证",
    "无风险",
    "百分百",
    "百分之百",
    "只赚不赔",
    "稳赚不赔",
]

FORBIDDEN_PATTERN = re.compile("|".join(FORBIDDEN_OUTPUT_WORDS), re.IGNORECASE)


# === Qualified investor whitelist ===
# For testing: insert test users here
# In production, this would be loaded from database
_QUALIFIED_WHITELIST = set()


def load_whitelist_from_env():
    """Load qualified investor whitelist from environment variable"""
    global _QUALIFIED_WHITELIST
    whitelist_str = os.getenv("QUALIFIED_INVESTOR_WHITELIST", "")
    if whitelist_str:
        _QUALIFIED_WHITELIST = set(w.strip() for w in whitelist_str.split(","))


def is_qualified_investor(user_open_id: str) -> bool:
    """Check if user is in qualified investor whitelist"""
    load_whitelist_from_env()
    return user_open_id in _QUALIFIED_WHITELIST


def add_to_whitelist(user_open_id: str):
    """Add a user to the qualified investor whitelist (for testing)"""
    _QUALIFIED_WHITELIST.add(user_open_id)


def get_whitelist() -> set:
    """Get current whitelist"""
    load_whitelist_from_env()
    return _QUALIFIED_WHITELIST.copy()


# === Risk warning template ===
RISK_WARNING = "【风险提示】本回答仅供参考，不构成投资建议。基金过往业绩不预示未来表现，投资有风险，入市需谨慎。如需了解更多，请咨询合规部门或专业投资顾问。"


@dataclass
class ComplianceCheckResult:
    """Result of compliance check"""
    allowed: bool
    reason: BlockReason
    message: str
    matched_keywords: List[str] = None

    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []


class ComplianceChecker:
    """Compliance checker for Q&A system"""

    def __init__(
        self,
        require_qualified: bool = True,
        enable_output_scan: bool = True,
    ):
        """
        Initialize compliance checker.

        Args:
            require_qualified: Whether to require qualified investor status for sensitive queries
            enable_output_scan: Whether to scan output for forbidden words
        """
        self.require_qualified = require_qualified
        self.enable_output_scan = enable_output_scan

    def check_query(
        self,
        question: str,
        user_open_id: Optional[str] = None,
    ) -> ComplianceCheckResult:
        """
        Check if a query is compliant.

        Args:
            question: User's question
            user_open_id: User's open ID (for qualified investor check)

        Returns:
            ComplianceCheckResult with allowed=True if query passes
        """
        # 1. Check for sensitive keywords
        matches = SENSITIVE_PATTERN.findall(question)
        if matches:
            # If sensitive content found, check qualified investor status
            if self.require_qualified and user_open_id:
                if not is_qualified_investor(user_open_id):
                    return ComplianceCheckResult(
                        allowed=False,
                        reason=BlockReason.NON_QUALIFIED_INVESTOR,
                        message="此问题涉及合格投资者专属信息，您的账号暂无权限查看。如需获取权限，请联系合规部门。",
                        matched_keywords=matches,
                    )

            # Even qualified investors get warning for sensitive queries
            # but we don't block them - just note it
            return ComplianceCheckResult(
                allowed=True,
                reason=BlockReason.SENSITIVE_KEYWORD,
                message="注意：此问题涉及敏感信息，已记录",
                matched_keywords=matches,
            )

        return ComplianceCheckResult(
            allowed=True,
            reason=BlockReason.NONE,
            message="Query passed compliance check",
        )

    def check_output(
        self,
        output: str,
    ) -> ComplianceCheckResult:
        """
        Check if output content is compliant.

        Args:
            output: Generated response

        Returns:
            ComplianceCheckResult with allowed=True if output passes
        """
        if not self.enable_output_scan:
            return ComplianceCheckResult(
                allowed=True,
                reason=BlockReason.NONE,
                message="Output scan disabled",
            )

        # Check for forbidden words
        matches = FORBIDDEN_PATTERN.findall(output)
        if matches:
            return ComplianceCheckResult(
                allowed=False,
                reason=BlockReason.FORBIDDEN_OUTPUT,
                message="回答中包含可能违反合规要求的内容，已自动处理",
                matched_keywords=matches,
            )

        return ComplianceCheckResult(
            allowed=True,
            reason=BlockReason.NONE,
            message="Output passed compliance check",
        )

    def sanitize_output(self, output: str) -> str:
        """
        Sanitize output by removing/replacing forbidden content.

        Args:
            output: Original output

        Returns:
            Sanitized output
        """
        sanitized = output

        # Replace forbidden phrases with safe alternatives
        replacements = {
            r"保本": "风险可控",
            r"保收益": "预期收益",
            r"稳赚": "有望获得",
            r"零风险": "低风险",
            r"保证收益": "预期收益",
            r"一定赚钱": "有机会获得收益",
            r"无风险": "风险较低",
            r"百分百": "高",
            r"百分之百": "高",
            r"只赚不赔": "有机会获得正收益",
            r"稳赚不赔": "有望获得正收益",
        }

        for forbidden, replacement in replacements.items():
            sanitized = re.sub(forbidden, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    def add_risk_warning(self, output: str) -> str:
        """Add risk warning to output if it mentions financial products"""
        # Check if output seems to be about specific financial products
        product_indicators = ["基金", "投资", "收益", "净值", "资产管理"]
        has_product_mention = any(indicator in output for indicator in product_indicators)

        if has_product_mention and RISK_WARNING not in output:
            return f"{output}\n\n{RISK_WARNING}"

        return output


# === Global compliance checker instance ===
_default_checker = None


def get_checker() -> ComplianceChecker:
    """Get global compliance checker instance"""
    global _default_checker
    if _default_checker is None:
        _default_checker = ComplianceChecker()
    return _default_checker


def check_query(question: str, user_open_id: str = None) -> ComplianceCheckResult:
    """Convenience function for query compliance check"""
    return get_checker().check_query(question, user_open_id)


def check_output(output: str) -> ComplianceCheckResult:
    """Convenience function for output compliance check"""
    return get_checker().check_output(output)


def sanitize_and_warn(output: str) -> str:
    """Sanitize output and add risk warning if needed"""
    checker = get_checker()
    sanitized = checker.sanitize_output(output)
    return checker.add_risk_warning(sanitized)


if __name__ == "__main__":
    # Quick test
    checker = ComplianceChecker()

    # Test sensitive query
    result = checker.check_query("A基金最新净值是多少？", user_open_id="test_user")
    print(f"Sensitive query test: allowed={result.allowed}, reason={result.reason}")

    # Add to whitelist and test again
    add_to_whitelist("test_user")
    result = checker.check_query("A基金最新净值是多少？", user_open_id="test_user")
    print(f"After whitelist: allowed={result.allowed}, reason={result.reason}")

    # Test forbidden output
    result = checker.check_output("这只基金保本且稳赚，绝对零风险")
    print(f"Forbidden output test: allowed={result.allowed}, reason={result.reason}")

    # Test sanitization
    sanitized = checker.sanitize_output("这只基金保本，绝对零风险")
    print(f"Sanitized: {sanitized}")
