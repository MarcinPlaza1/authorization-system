from setuptools import setup, find_packages

setup(
    name="fastapi-app",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.68.0",
        "sqlalchemy>=1.4.23",
        "pytest>=6.2.5",
        "pytest-asyncio>=0.15.1",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.5",
        "email-validator>=1.1.3",
        "aioredis>=2.0.0",
        "httpx>=0.19.0",
    ],
) 