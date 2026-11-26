using System.Windows.Forms;
using Microsoft.Win32;

namespace MyMascot;

public static class AutoStart
{
	private const string RunKey = "Software\\Microsoft\\Windows\\CurrentVersion\\Run";

	private const string ValueName = "병아리대원";

	private static string Command => "\"" + Application.ExecutablePath + "\"";

	public static bool IsEnabled()
	{
		try
		{
			using RegistryKey registryKey = Registry.CurrentUser.OpenSubKey("Software\\Microsoft\\Windows\\CurrentVersion\\Run");
			return registryKey != null && registryKey.GetValue("병아리대원") != null;
		}
		catch
		{
			return false;
		}
	}

	public static void Set(bool on)
	{
		try
		{
			using RegistryKey registryKey = Registry.CurrentUser.CreateSubKey("Software\\Microsoft\\Windows\\CurrentVersion\\Run");
			if (on)
			{
				registryKey.SetValue("병아리대원", Command);
			}
			else if (registryKey.GetValue("병아리대원") != null)
			{
				registryKey.DeleteValue("병아리대원");
			}
		}
		catch
		{
		}
	}

	public static void RefreshPathIfEnabled()
	{
		try
		{
			using RegistryKey registryKey = Registry.CurrentUser.OpenSubKey("Software\\Microsoft\\Windows\\CurrentVersion\\Run", writable: true);
			if (registryKey != null && registryKey.GetValue("병아리대원") is string text && text != Command)
			{
				registryKey.SetValue("병아리대원", Command);
			}
		}
		catch
		{
		}
	}
}
