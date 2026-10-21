"""Run the local Go redaction → Python classification → audit-chain slice."""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = (
    "John Doe (SSN 123-45-6789) reports a pothole on Main Street. "
    "Contact john.doe@example.gov at 555-123-4567."
)


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def generate_mtls_certificates(directory: Path) -> tuple[Path, Path, Path, Path, Path]:
    ca_key = directory / "ca.key"
    ca_cert = directory / "ca.crt"
    server_key = directory / "server.key"
    server_csr = directory / "server.csr"
    server_cert = directory / "server.crt"
    client_key = directory / "client.key"
    client_csr = directory / "client.csr"
    client_cert = directory / "client.crt"

    run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(ca_key), "-out", str(ca_cert), "-days", "1",
            "-subj", "/CN=CivicAI local slice CA",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign",
        ],
        cwd=directory,
    )
    run(
        [
            "openssl", "req", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(server_key), "-out", str(server_csr),
            "-subj", "/CN=localhost",
        ],
        cwd=directory,
    )
    server_extensions = directory / "server.ext"
    server_extensions.write_text(
        "subjectAltName=DNS:localhost,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n",
        encoding="ascii",
    )
    run(
        [
            "openssl", "x509", "-req", "-in", str(server_csr),
            "-CA", str(ca_cert), "-CAkey", str(ca_key), "-CAcreateserial",
            "-out", str(server_cert), "-days", "1", "-extfile", str(server_extensions),
        ],
        cwd=directory,
    )
    run(
        [
            "openssl", "req", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(client_key), "-out", str(client_csr),
            "-subj", "/CN=local-slice-tenant",
        ],
        cwd=directory,
    )
    client_extensions = directory / "client.ext"
    client_extensions.write_text("extendedKeyUsage=clientAuth\n", encoding="ascii")
    run(
        [
            "openssl", "x509", "-req", "-in", str(client_csr),
            "-CA", str(ca_cert), "-CAkey", str(ca_key), "-CAcreateserial",
            "-out", str(client_cert), "-days", "1", "-extfile", str(client_extensions),
        ],
        cwd=directory,
    )
    return ca_cert, server_cert, server_key, client_cert, client_key


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_for_service(url: str, process: subprocess.Popen[bytes], name: str) -> None:
    deadline = time.monotonic() + 120
    with httpx.Client(timeout=2) as client:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"{name} exited during startup")
            try:
                if client.get(url).status_code == 200:
                    return
            except httpx.HTTPError:
                time.sleep(0.2)
    raise RuntimeError(f"{name} did not become ready")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-nextjs",
        action="store_true",
        help="also run the optional Next.js /api/triage path",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="civicai-slice-") as temporary_directory:
        directory = Path(temporary_directory)
        ca_cert, server_cert, server_key, client_cert, client_key = generate_mtls_certificates(directory)
        port = available_port()
        address = f"127.0.0.1:{port}"
        environment = os.environ.copy()
        environment.update(
            {
                "AUDIT_ADDR": address,
                "MTLS_CERT_FILE": str(server_cert),
                "MTLS_KEY_FILE": str(server_key),
                "MTLS_CLIENT_CA_FILE": str(ca_cert),
            }
        )
        tls_context = ssl.create_default_context(cafile=str(ca_cert))
        tls_context.load_cert_chain(str(client_cert), str(client_key))
        binary = directory / "civicai-ingest"
        run(["go", "build", "-o", str(binary), "./cmd/ingest"], cwd=ROOT, env=environment)
        processes: list[subprocess.Popen[bytes]] = []
        server = subprocess.Popen(
            [str(binary)],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(server)
        endpoint = f"https://localhost:{port}"
        try:
            with httpx.Client(
                verify=tls_context,
                timeout=0.5,
            ) as health_client:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    if server.poll() is not None:
                        raise RuntimeError("Go ingest server exited during startup")
                    try:
                        if health_client.get(f"{endpoint}/healthz").status_code == 200:
                            break
                    except httpx.HTTPError:
                        time.sleep(0.2)
                else:
                    raise RuntimeError("Go ingest server did not become ready")

            api_port = available_port()
            python_environment = environment.copy()
            python_environment.update(
                {
                    "DATABASE_ENABLED": "false",
                    "MOCK_LLM": "true",
                    "RAG_ENABLED": "false",
                    "SYNC_MODE": "true",
                    "SKIP_DOTENV": "true",
                    "PYTHONPATH": str(ROOT),
                }
            )
            python_server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                ],
                cwd=directory,
                env=python_environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            processes.append(python_server)
            wait_for_service(f"http://127.0.0.1:{api_port}/health", python_server, "Python API")

            if args.with_nextjs:
                frontend_port = available_port()
                frontend_environment = environment.copy()
                frontend_environment.update(
                    {
                        "GO_INGEST_URL": f"{endpoint}/v1/redact",
                        "GO_INGEST_CLIENT_CERT": client_cert.read_text(encoding="ascii"),
                        "GO_INGEST_CLIENT_KEY": client_key.read_text(encoding="ascii"),
                        "GO_INGEST_SERVER_CA": ca_cert.read_text(encoding="ascii"),
                        "NEXT_PUBLIC_API_BASE": f"http://127.0.0.1:{api_port}",
                        "NEXT_TELEMETRY_DISABLED": "1",
                    }
                )
                frontend_project = directory / "frontend"
                shutil.copytree(
                    ROOT / "frontend",
                    frontend_project,
                    ignore=shutil.ignore_patterns("node_modules", ".next", ".vercel"),
                )
                (frontend_project / "node_modules").symlink_to(
                    ROOT / "frontend" / "node_modules",
                    target_is_directory=True,
                )
                frontend_server = subprocess.Popen(
                    [
                        "node",
                        "node_modules/next/dist/bin/next",
                        "dev",
                        "--hostname",
                        "127.0.0.1",
                        "--port",
                        str(frontend_port),
                    ],
                    cwd=frontend_project,
                    env=frontend_environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                processes.append(frontend_server)
                wait_for_service(
                    f"http://127.0.0.1:{frontend_port}/workflow",
                    frontend_server,
                    "Next.js frontend",
                )
                triage_url = f"http://127.0.0.1:{frontend_port}/api/triage"
                triage_payload = {"text": DOCUMENT, "source_type": "text"}
                timeout = 35
            else:
                with httpx.Client(verify=tls_context, timeout=5) as ingest_client:
                    redaction_response = ingest_client.post(
                        f"{endpoint}/v1/redact",
                        json={"text": DOCUMENT, "source_type": "text"},
                    )
                redaction_response.raise_for_status()
                redaction = redaction_response.json()
                redacted_text = redaction.get("redacted_text")
                if not isinstance(redacted_text, str) or any(
                    value in redacted_text
                    for value in ("123-45-6789", "john.doe@example.gov", "555-123-4567")
                ):
                    raise RuntimeError("Go ingest returned unredacted text")
                triage_url = f"http://127.0.0.1:{api_port}/api/v1/process"
                triage_payload = {"text": redacted_text, "source_type": "text"}
                timeout = 35

            with httpx.Client(timeout=timeout) as triage_client:
                response = triage_client.post(triage_url, json=triage_payload)
            response.raise_for_status()
            result = response.json()
            redacted_text = result.get("redacted_text")
            if not isinstance(redacted_text, str) or any(
                value in redacted_text
                for value in ("123-45-6789", "john.doe@example.gov", "555-123-4567")
            ):
                raise RuntimeError("The frontend workflow returned unredacted text")
            decision = result["decision"]
            if not isinstance(decision, dict) or decision.get("department") != "Public Works":
                raise RuntimeError("Python classification returned an unexpected route")
            audit_hash = result.get("audit_hash")
            if not isinstance(audit_hash, str) or len(audit_hash) != 64:
                raise RuntimeError("Python API did not return an audit-chain hash")

            audit_path = directory / "data" / "audit-chain.jsonl"
            verification = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "verify_audit.py"), str(audit_path)],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            if verification.returncode != 0:
                raise RuntimeError(verification.stdout.strip() or "Audit-chain verification failed")
            print(f"Route: {decision['department']}")
            print(f"Audit hash: {audit_hash}")
            print(verification.stdout.strip())
            return 0
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
            for process in reversed(processes):
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
