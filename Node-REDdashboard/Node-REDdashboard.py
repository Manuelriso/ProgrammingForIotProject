import subprocess

def get_container_status(name):
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Status}}", name],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

def start_nodered():
    subprocess.run([
        "docker", "run", "-d",
        "-p", "1880:1880",
        "--name", "mynodered",
        "nodered/node-red"
    ])

def main():
    container_name = "mynodered"
    status = get_container_status(container_name)

    if status is None:
        print("Creazione container")
        start_nodered()
    elif status == "exited" or status == "created":
        print("Riavvio container")
        subprocess.run(["docker", "start", container_name])
    elif status == "running":
        print("No action")
    else:
        print(f"Stato sconosciuto del container: '{status}'")

if __name__ == "__main__":
    main()
