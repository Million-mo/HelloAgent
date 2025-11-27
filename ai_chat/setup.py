"""Setup configuration for ai_chat package."""

from setuptools import setup, find_packages
import os

# 读取 requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(requirements_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# 读取 README (如果存在)
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "AI Chat - A multi-agent system with LLM integration"

def get_packages():
    """Get all packages with ai_chat prefix.
    
    Maps src/* to ai_chat.* packages.
    For example: src/agents -> ai_chat.agents
    """
    # Find all packages in the src directory
    src_packages = find_packages(where='src')
    # Return ai_chat as root package plus all subpackages with ai_chat prefix
    return ['ai_chat'] + ['ai_chat.' + p for p in src_packages]

setup(
    name="ai-chat",
    version="0.1.0",
    author="AI Chat Team",
    author_email="",
    description="A multi-agent system with LLM integration",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="",
    # 将 src 目录映射为 ai_chat 包
    package_dir={'ai_chat': 'src'},
    packages=get_packages(),
    package_data={'ai_chat': ['*']},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'ai-chat-server=ai_chat.app:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
