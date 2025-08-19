from setuptools import setup, find_packages

setup(
    name="dn_solution",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        # 기본 요구사항은 requirements.txt에서 관리
    ],
    author="DN Solution Team",
    author_email="admin@dn-solution.com",
    description="DN Solution Project",
    keywords="django, web, solution",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
)
