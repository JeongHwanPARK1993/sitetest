using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace MyMascot;

public class SpeechBubbleForm : Form
{
	private const int MaxTextWidth = 200;

	internal const int CloudMargin = 13;

	private const int CloudPadX = 10;

	private const int CloudPadY = 6;

	private const int CloudTailH = 24;

	internal const float CloudLineW = 2.2f;

	private const float CloudPuffR = 17f;

	private string currentText = "";

	private static readonly Color CloudLine = Color.FromArgb(255, 95, 80, 70);

	private static readonly Color CloudFill = Color.White;

	protected override CreateParams CreateParams
	{
		get
		{
			CreateParams createParams = base.CreateParams;
			createParams.ExStyle |= 0x80000;
			return createParams;
		}
	}

	[DllImport("user32.dll", SetLastError = true)]
	private static extern bool UpdateLayeredWindow(IntPtr hwnd, IntPtr hdcDst, ref MascotForm.POINTAPI pptDst, ref MascotForm.SIZEAPI psize, IntPtr hdcSrc, ref MascotForm.POINTAPI pptSrc, int crKey, ref MascotForm.BLENDFUNCTION pblend, int dwFlags);

	[DllImport("user32.dll")]
	private static extern IntPtr GetDC(IntPtr hWnd);

	[DllImport("user32.dll")]
	private static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);

	[DllImport("gdi32.dll")]
	private static extern IntPtr CreateCompatibleDC(IntPtr hDC);

	[DllImport("gdi32.dll")]
	private static extern IntPtr SelectObject(IntPtr hDC, IntPtr hObject);

	[DllImport("gdi32.dll")]
	private static extern bool DeleteObject(IntPtr hObject);

	[DllImport("gdi32.dll")]
	private static extern bool DeleteDC(IntPtr hDC);

	public SpeechBubbleForm()
	{
		((Form)this).FormBorderStyle = (FormBorderStyle)0;
		((Form)this).ShowInTaskbar = false;
		((Form)this).TopMost = true;
		((Control)this).Width = 1;
		((Control)this).Height = 1;
	}

	public void ShowAt(string text, int anchorX, int anchorY)
	{
		bool flag = text != currentText || ((Control)this).Width <= 1;
		if (flag)
		{
			currentText = text;
			SizeToText(text);
		}
		Point point = new Point(anchorX - 20, anchorY - ((Control)this).Height);
		if (flag)
		{
			((Form)this).Location = point;
			Redraw(text);
		}
		else if (((Form)this).Location != point)
		{
			((Form)this).Location = point;
		}
	}

	private Font BubbleFont()
	{
		//IL_000b: Unknown result type (might be due to invalid IL or missing references)
		//IL_0011: Expected O, but got Unknown
		return new Font("맑은 고딕", 10f, (FontStyle)1);
	}

	private List<string> WrapLines(string text, Font font, Graphics g, float maxWidth)
	{
		List<string> list = new List<string>();
		string[] array = text.Split(new char[1] { '\n' });
		foreach (string text2 in array)
		{
			string[] array2 = text2.Split(new char[1] { ' ' });
			string text3 = "";
			string[] array3 = array2;
			foreach (string text4 in array3)
			{
				string text5 = ((text3.Length == 0) ? text4 : (text3 + " " + text4));
				float width = g.MeasureString(text5, font).Width;
				if (width <= maxWidth || text3.Length == 0)
				{
					text3 = text5;
					continue;
				}
				list.Add(text3);
				text3 = text4;
			}
			if (text3.Length > 0)
			{
				list.Add(text3);
			}
		}
		return list;
	}

	private void SizeToText(string text)
	{
		//IL_0002: Unknown result type (might be due to invalid IL or missing references)
		//IL_0008: Expected O, but got Unknown
		Bitmap val = new Bitmap(1, 1);
		try
		{
			Graphics val2 = Graphics.FromImage((Image)(object)val);
			try
			{
				Font val3 = BubbleFont();
				try
				{
					List<string> list = WrapLines(text, val3, val2, 182f);
					float num = 0f;
					foreach (string item in list)
					{
						float width = val2.MeasureString(item, val3).Width;
						if (width > num)
						{
							num = width;
						}
					}
					float height = val3.GetHeight(val2);
					((Control)this).Width = Math.Max(124, (int)num + 8 + 46);
					((Control)this).Height = Math.Max(70, (int)(height * (float)list.Count) + 38) + 24;
				}
				finally
				{
					((IDisposable)val3)?.Dispose();
				}
			}
			finally
			{
				((IDisposable)val2)?.Dispose();
			}
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	internal static List<RectangleF> CloudShapes(RectangleF core)
	{
		List<RectangleF> list = new List<RectangleF>();
		RectangleF rectangleF = CloudPuffPath(core);
		PointF[] array = new PointF[4]
		{
			new PointF(rectangleF.X, rectangleF.Y),
			new PointF(rectangleF.Right, rectangleF.Y),
			new PointF(rectangleF.Right, rectangleF.Bottom),
			new PointF(rectangleF.X, rectangleF.Bottom)
		};
		int num = 0;
		for (int i = 0; i < 4; i++)
		{
			PointF pointF = array[i];
			PointF pointF2 = array[(i + 1) % 4];
			float num2 = Math.Abs(pointF2.X - pointF.X) + Math.Abs(pointF2.Y - pointF.Y);
			int num3 = Math.Max(1, (int)Math.Round(num2 / 22f));
			int num4 = 0;
			while (num4 < num3)
			{
				float num5 = (float)num4 / (float)num3;
				float num6 = 17f - (float)(num * 7 % 3) * 1.5f;
				float num7 = pointF.X + (pointF2.X - pointF.X) * num5;
				float num8 = pointF.Y + (pointF2.Y - pointF.Y) * num5;
				list.Add(new RectangleF(num7 - num6, num8 - num6, num6 * 2f, num6 * 2f));
				num4++;
				num++;
			}
		}
		return list;
	}

	internal static RectangleF CloudPuffPath(RectangleF core)
	{
		float num = -8f;
		RectangleF result = RectangleF.Inflate(core, num, num);
		if (result.Width < 0f)
		{
			result.X += result.Width / 2f;
			result.Width = 0f;
		}
		if (result.Height < 0f)
		{
			result.Y += result.Height / 2f;
			result.Height = 0f;
		}
		return result;
	}

	private static void DrawBlob(Graphics g, List<RectangleF> ellipses, RectangleF? core, float lineW)
	{
		DrawBlob(g, ellipses, core, lineW, CloudFill);
	}

	internal static void DrawBlob(Graphics g, List<RectangleF> ellipses, RectangleF? core, float lineW, Color fillColor)
	{
		//IL_000a: Unknown result type (might be due to invalid IL or missing references)
		//IL_0010: Expected O, but got Unknown
		//IL_00d2: Unknown result type (might be due to invalid IL or missing references)
		//IL_00d8: Expected O, but got Unknown
		//IL_0119: Unknown result type (might be due to invalid IL or missing references)
		//IL_0120: Expected O, but got Unknown
		SolidBrush val = new SolidBrush(Color.FromArgb(28, 0, 0, 0));
		try
		{
			foreach (RectangleF ellipsis in ellipses)
			{
				g.FillEllipse((Brush)(object)val, ellipsis.X, ellipsis.Y + 2.5f, ellipsis.Width, ellipsis.Height);
			}
			if (core.HasValue)
			{
				g.FillRectangle((Brush)(object)val, core.Value.X, core.Value.Y + 2.5f, core.Value.Width, core.Value.Height);
			}
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
		Pen val2 = new Pen(CloudLine, lineW * 2f);
		try
		{
			foreach (RectangleF ellipsis2 in ellipses)
			{
				g.DrawEllipse(val2, ellipsis2);
			}
		}
		finally
		{
			((IDisposable)val2)?.Dispose();
		}
		SolidBrush val3 = new SolidBrush(fillColor);
		try
		{
			foreach (RectangleF ellipsis3 in ellipses)
			{
				g.FillEllipse((Brush)(object)val3, ellipsis3);
			}
			if (core.HasValue)
			{
				g.FillRectangle((Brush)(object)val3, core.Value);
			}
		}
		finally
		{
			((IDisposable)val3)?.Dispose();
		}
	}

	private void Redraw(string text)
	{
		//IL_0011: Unknown result type (might be due to invalid IL or missing references)
		//IL_0017: Expected O, but got Unknown
		//IL_0127: Unknown result type (might be due to invalid IL or missing references)
		//IL_012e: Expected O, but got Unknown
		//IL_012e: Unknown result type (might be due to invalid IL or missing references)
		//IL_0135: Expected O, but got Unknown
		Bitmap val = new Bitmap(((Control)this).Width, ((Control)this).Height, (PixelFormat)2498570);
		try
		{
			Graphics val2 = Graphics.FromImage((Image)(object)val);
			try
			{
				Font val3 = BubbleFont();
				try
				{
					val2.Clear(Color.Transparent);
					val2.SmoothingMode = (SmoothingMode)4;
					val2.TextRenderingHint = (TextRenderingHint)3;
					float num = 13f;
					RectangleF core = new RectangleF(num, num, (float)((Control)this).Width - 2f * num, (float)(((Control)this).Height - 24) - 2f * num);
					DrawBlob(val2, CloudShapes(core), CloudPuffPath(core), 2.2f);
					DrawBlob(val2, new List<RectangleF>
					{
						new RectangleF(17f, core.Bottom + num - 1f, 13f, 11f)
					}, null, 2.2f);
					DrawBlob(val2, new List<RectangleF>
					{
						new RectangleF(7f, ((Control)this).Height - 10, 8f, 7f)
					}, null, 2.2f);
					SolidBrush val4 = new SolidBrush(Color.FromArgb(255, 55, 45, 40));
					try
					{
						StringFormat val5 = new StringFormat();
						val5.Alignment = (StringAlignment)1;
						StringFormat val6 = val5;
						try
						{
							List<string> list = WrapLines(text, val3, val2, core.Width - 20f - 4f);
							float height = val3.GetHeight(val2);
							float num2 = height * (float)list.Count;
							float num3 = core.Y + (core.Height - num2) / 2f;
							float num4 = core.X + core.Width / 2f;
							for (int i = 0; i < list.Count; i++)
							{
								val2.DrawString(list[i], val3, (Brush)(object)val4, num4, num3 + (float)i * height, val6);
							}
						}
						finally
						{
							((IDisposable)val6)?.Dispose();
						}
					}
					finally
					{
						((IDisposable)val4)?.Dispose();
					}
				}
				finally
				{
					((IDisposable)val3)?.Dispose();
				}
			}
			finally
			{
				((IDisposable)val2)?.Dispose();
			}
			SetBitmap(val);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	private void SetBitmap(Bitmap bitmap)
	{
		IntPtr dC = GetDC(IntPtr.Zero);
		IntPtr intPtr = CreateCompatibleDC(dC);
		IntPtr intPtr2 = IntPtr.Zero;
		IntPtr hObject = IntPtr.Zero;
		try
		{
			intPtr2 = bitmap.GetHbitmap(Color.FromArgb(0));
			hObject = SelectObject(intPtr, intPtr2);
			MascotForm.SIZEAPI psize = new MascotForm.SIZEAPI(((Image)bitmap).Width, ((Image)bitmap).Height);
			MascotForm.POINTAPI pptSrc = new MascotForm.POINTAPI(0, 0);
			MascotForm.POINTAPI pptDst = new MascotForm.POINTAPI(((Control)this).Left, ((Control)this).Top);
			MascotForm.BLENDFUNCTION pblend = new MascotForm.BLENDFUNCTION
			{
				BlendOp = 0,
				BlendFlags = 0,
				SourceConstantAlpha = byte.MaxValue,
				AlphaFormat = 1
			};
			UpdateLayeredWindow(((Control)this).Handle, dC, ref pptDst, ref psize, intPtr, ref pptSrc, 0, ref pblend, 2);
		}
		finally
		{
			ReleaseDC(IntPtr.Zero, dC);
			if (intPtr2 != IntPtr.Zero)
			{
				SelectObject(intPtr, hObject);
				DeleteObject(intPtr2);
			}
			DeleteDC(intPtr);
		}
	}
}
