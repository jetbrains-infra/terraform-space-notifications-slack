import space.jetbrains.api.runtime.*

job("TF - Validate") {
    container("hashicorp/terraform:1.0.8") {
        entrypoint("/bin/sh")
        args(
            "-ec",
            """
                set -o pipefail
                terraform init -backend=false -force-copy -no-color > /dev/null
                terraform validate -no-color
            """.trimIndent()
        )
    }
}

job("TF - Fmt") {
    container("hashicorp/terraform:1.0.8") {
        entrypoint("/bin/sh")
        args(
            "-ec",
            "terraform fmt -check -recursive -diff && echo terraform fmt has been checked, everything is good"
        )
    }
}

job("TF - Lint") {
    container("ghcr.io/terraform-linters/tflint-bundle:latest") {
        entrypoint("/bin/sh")
        args(
                "-ec",
                """
                    set -o pipefail
                    tflint --init
                    tflint
                """.trimIndent()
        )
    }
}