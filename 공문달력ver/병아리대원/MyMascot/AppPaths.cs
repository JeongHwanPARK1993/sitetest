using System;
using System.IO;
using System.Windows.Forms;

namespace MyMascot;

public static class AppPaths
{
	public static readonly string DataDir = InitDataDir();

	private static string InitDataDir()
	{
		string text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "병아리대원");
		Directory.CreateDirectory(text);
		return text;
	}

	public static string Config(string name)
	{
		string text = Path.Combine(DataDir, name);
		if (!File.Exists(text))
		{
			string text2 = Path.Combine(Application.StartupPath, name);
			try
			{
				if (File.Exists(text2))
				{
					File.Copy(text2, text);
				}
			}
			catch
			{
			}
		}
		return text;
	}
}
