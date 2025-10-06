#!/usr/bin/env python3
"""Unit tests for the fan unlock helper routines."""

import subprocess
import unittest
from unittest import mock

import niraj


class FanUnlockTests(unittest.TestCase):
    """Validate that the unlock helper orchestrates commands correctly."""

    @mock.patch("niraj.check_fan_control_available")
    @mock.patch("niraj.Path.exists")
    @mock.patch("niraj.shutil.which")
    @mock.patch("niraj.subprocess.run")
    def test_attempt_unlock_runs_expected_commands(
        self,
        mock_run,
        mock_which,
        mock_exists,
        mock_check,
    ) -> None:
        """Ensure unlock routine calls critical commands when tools exist."""

        command_log = []

        def which_side_effect(cmd: str):
            mapping = {
                "sudo": "/usr/bin/sudo",
                "nvidia-settings": "/usr/bin/nvidia-settings",
                "nvidia-smi": "/usr/bin/nvidia-smi",
                "nvidia-xconfig": "/usr/bin/nvidia-xconfig",
                "systemctl": "/usr/bin/systemctl",
            }
            return mapping.get(cmd)

        def run_side_effect(cmd, *args, **kwargs):
            command_log.append(" ".join(cmd))
            if "nvidia-settings" in cmd and "-q" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="Attribute 'GPUFanControlState' (value: 1)\n", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        mock_which.side_effect = which_side_effect
        mock_exists.return_value = True
        mock_run.side_effect = run_side_effect
        mock_check.side_effect = [
            {
                "available": False,
                "nvidia_smi": True,
                "nvidia_settings": True,
                "gpu_count": 1,
                "message": "manual control disabled",
                "oem_locked": True,
                "requires_display": False,
                "nvidia_smi_error": None,
            },
            {
                "available": True,
                "nvidia_smi": True,
                "nvidia_settings": True,
                "gpu_count": 1,
                "message": "manual control ok",
                "oem_locked": False,
                "requires_display": False,
                "nvidia_smi_error": None,
            },
        ]

        result = niraj.attempt_unlock_fan_control()

        self.assertTrue(result["success"])
        self.assertTrue(any("nvidia-xconfig" in cmd for cmd in command_log))
        self.assertTrue(any("GPUFanControlState" in cmd for cmd in command_log))
        self.assertEqual(result["post_check"]["message"], "manual control ok")

    @mock.patch("niraj.shutil.which", return_value=None)
    def test_attempt_unlock_requires_sudo(self, mock_which) -> None:
        """If sudo is missing the unlock routine should not proceed."""

        result = niraj.attempt_unlock_fan_control()

        self.assertFalse(result["success"])
        self.assertTrue(any("sudo" in err.lower() for err in result["errors"]))

    @mock.patch("niraj.check_fan_control_available")
    @mock.patch("niraj.shutil.which")
    @mock.patch("niraj.subprocess.run")
    def test_attempt_unlock_detects_missing_gpu(self, mock_run, mock_which, mock_check) -> None:
        """Unlock routine should abort early when no NVIDIA GPU is detected."""

        def which_side_effect(cmd: str):
            mapping = {
                "sudo": "/usr/bin/sudo",
                "nvidia-settings": "/usr/bin/nvidia-settings",
                "nvidia-smi": "/usr/bin/nvidia-smi",
            }
            return mapping.get(cmd)

        mock_which.side_effect = which_side_effect
        mock_check.return_value = {
            "available": False,
            "nvidia_smi": True,
            "nvidia_settings": True,
            "gpu_count": 0,
            "message": "nvidia-smi did not report any NVIDIA GPUs.",
            "oem_locked": False,
            "requires_display": False,
            "nvidia_smi_error": None,
        }

        result = niraj.attempt_unlock_fan_control()

        self.assertFalse(result["success"])
        self.assertEqual(result["steps"], [])
        combined_errors = " ".join(result["errors"])
        self.assertIn("nvidia-smi did not report any NVIDIA GPUs", combined_errors)
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
