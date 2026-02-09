from setuptools import setup, find_packages

setup(
    name='molchoctl',
    version='1.0.0',
    packages=find_packages(),
    py_modules=['molchoctl'],  # This includes your main script file
    include_package_data=True,
    install_requires=[
        'Click',
        'boto3',
        'rich',
    ],
    entry_points={
        'console_scripts': [
            # THE MAGIC LINE:
            # command_name = python_file:function_name
            'molchoctl = molchoctl:cli',
        ],
    },
)
