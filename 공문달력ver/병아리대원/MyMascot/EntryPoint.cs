using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace MyMascot;

public static class EntryPoint
{
	[STAThread]
	public static void Main()
	{
		bool createdNew;
		using Mutex obj = new Mutex(initiallyOwned: true, "Local\\병아리대원_SingleInstance", out createdNew);
		if (createdNew)
		{
			Application.SetUnhandledExceptionMode((UnhandledExceptionMode)2);
			Application.ThreadException += delegate(object s, ThreadExceptionEventArgs e)
			{
				LogError(e.Exception);
			};
			AppDomain.CurrentDomain.UnhandledException += delegate(object s, UnhandledExceptionEventArgs e)
			{
				LogError(e.ExceptionObject as Exception);
			};
			Application.EnableVisualStyles();
			Application.SetCompatibleTextRenderingDefault(false);
			Application.Run((ApplicationContext)(object)new TrayAppContext());
			GC.KeepAlive(obj);
		}
	}

	private static void LogError(Exception ex)
	{
		try
		{
			string text = Path.Combine(AppPaths.DataDir, "error.log");
			if (File.Exists(text) && new FileInfo(text).Length > 204800)
			{
				File.Delete(text);
			}
			File.AppendAllText(text, string.Concat(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"), "  ", ex, Environment.NewLine), Encoding.UTF8);
		}
		catch
		{
		}
	}
}
