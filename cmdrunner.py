import subprocess

class CmdRunner:

    __logger = None

    def __init__(self, logger):
        self.__logger = logger

    def run(self, args):
        completed_process = subprocess.run(
            args,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )

        exit_status = completed_process.returncode
        stdout = completed_process.stdout.decode("utf-8")

        if exit_status != 0:
            stderr = completed_process.stderr.decode("utf-8")
            raise Exception('Got exit status: ' + str(exit_status) + " stdout: " + stdout + " stderr: " + stderr)

        return stdout
