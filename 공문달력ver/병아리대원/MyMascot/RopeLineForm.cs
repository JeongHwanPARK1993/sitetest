using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace MyMascot;

public class RopeLineForm : Form
{
	private const int StripWidth = 64;

	private const int RetractTicks = 10;

	private Timer retractTimer;

	private int retractTick;

	private static readonly Color RopeEdge = Color.FromArgb(255, 70, 10, 0);

	private static readonly Color RopeFill = Color.FromArgb(255, 250, 140, 45);

	private int lastGapTop;

	private int lastGapBottom;

	private float topDx;

	private float bottomDx;

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

	public RopeLineForm()
	{
		((Form)this).FormBorderStyle = (FormBorderStyle)0;
		((Form)this).ShowInTaskbar = false;
		((Form)this).TopMost = true;
		((Control)this).Width = 64;
		((Control)this).Height = 1;
	}

	public void PlaceAt(int centerX, int topY, int bottomY)
	{
		if (retractTimer != null)
		{
			retractTimer.Stop();
		}
		int height = Math.Max(1, bottomY - topY);
		((Control)this).Bounds = new Rectangle(centerX - 32, topY, 64, height);
		DrawRope(0.0);
	}

	public void RetractAndHide()
	{
		//IL_000b: Unknown result type (might be due to invalid IL or missing references)
		//IL_0015: Expected O, but got Unknown
		if (retractTimer == null)
		{
			retractTimer = new Timer();
			retractTimer.Interval = 30;
			retractTimer.Tick += delegate
			{
				retractTick++;
				double num = (double)retractTick / 10.0;
				if (num >= 1.0)
				{
					retractTimer.Stop();
					((Control)this).Hide();
				}
				else
				{
					Render(0.0, (double)lastGapTop * (1.0 - num * num), 0.0, lastGapBottom, lastGapBottom, 0.0);
				}
			};
		}
		retractTick = 0;
		retractTimer.Stop();
		retractTimer.Start();
	}

	public void DrawRope(double visibleFraction)
	{
		DrawRope(visibleFraction, 0.0, 0, 0, 0f, 0f);
	}

	public void DrawRope(double visibleFraction, double whip, int gapTop, int gapBottom, float topOffset, float bottomOffset)
	{
		lastGapTop = gapTop;
		lastGapBottom = gapBottom;
		topDx = topOffset;
		bottomDx = bottomOffset;
		double num = Math.Max(0.0, Math.Min(1.0, visibleFraction));
		int belowEnd = gapBottom + (int)((double)(((Control)this).Height - gapBottom) * num);
		Render(0.0, gapTop, 0.0, gapBottom, belowEnd, whip);
	}

	public void DrawRopeUp(double upFraction, double whip, int gapTop, int gapBottom, int belowEnd, float topOffset, float bottomOffset)
	{
		lastGapTop = gapTop;
		lastGapBottom = gapBottom;
		topDx = topOffset;
		bottomDx = bottomOffset;
		double num = Math.Max(0.0, Math.Min(1.0, upFraction));
		Render((double)gapTop * (1.0 - num), gapTop, whip, gapBottom, Math.Min(((Control)this).Height, belowEnd), 0.0);
	}

	private void Render(double aboveTop, double aboveBottom, double topWhip, int gapBottom, int belowEnd, double bottomWhip)
	{
		//IL_0014: Unknown result type (might be due to invalid IL or missing references)
		//IL_001a: Expected O, but got Unknown
		Bitmap val = new Bitmap(((Control)this).Width, ((Control)this).Height, (PixelFormat)2498570);
		try
		{
			Graphics val2 = Graphics.FromImage((Image)(object)val);
			try
			{
				val2.Clear(Color.Transparent);
				val2.SmoothingMode = (SmoothingMode)4;
				float num = 32f;
				double num2 = (double)Environment.TickCount / 1000.0;
				double num3 = 26.0;
				float num4 = num + topDx;
				double num5 = aboveBottom - aboveTop;
				if (num5 > 0.5)
				{
					if (topWhip <= 0.0)
					{
						DrawCord(val2, new PointF[2]
						{
							new PointF(num4, (float)aboveTop),
							new PointF(num4, (float)aboveBottom)
						});
					}
					else
					{
						int num6 = Math.Max(2, (int)(num5 / 10.0));
						PointF[] array = new PointF[num6 + 1];
						for (int i = 0; i <= num6; i++)
						{
							double num7 = (double)i / (double)num6;
							double num8 = aboveBottom - num5 * num7;
							double num9 = topWhip * num3 * Math.Pow(num7, 1.6) * Math.Sin(num2 * 14.0 + num8 * 0.035);
							ref PointF reference = ref array[i];
							reference = new PointF((float)Math.Max(4.0, Math.Min(60.0, (double)num4 + num9)), (float)num8);
						}
						DrawCord(val2, array);
					}
				}
				if (belowEnd > gapBottom)
				{
					List<PointF> list = new List<PointF>();
					list.Add(new PointF(num + bottomDx, gapBottom));
					int num10 = belowEnd - gapBottom;
					if (num10 > 1)
					{
						int num11 = Math.Max(2, num10 / 10);
						for (int j = 1; j <= num11; j++)
						{
							double num12 = (double)j / (double)num11;
							double num13 = (double)gapBottom + (double)num10 * num12;
							double num14 = bottomWhip * num3 * Math.Pow(num12, 1.6) * Math.Sin(num2 * 14.0 - num13 * 0.035);
							double num15 = Math.Sin(num13 * 0.04) * 1.5 * num12;
							double num16 = Math.Max(4.0, Math.Min(60.0, (double)(num + bottomDx) + num14 + num15));
							list.Add(new PointF((float)num16, (float)num13));
						}
					}
					if (list.Count >= 2)
					{
						DrawCord(val2, list.ToArray());
					}
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

	private static void DrawCord(Graphics g, PointF[] pts)
	{
		//IL_000a: Unknown result type (might be due to invalid IL or missing references)
		//IL_0010: Expected O, but got Unknown
		//IL_0045: Unknown result type (might be due to invalid IL or missing references)
		//IL_004b: Expected O, but got Unknown
		Pen val = new Pen(RopeEdge, 3.2f);
		val.LineJoin = (LineJoin)2;
		val.StartCap = (LineCap)2;
		val.EndCap = (LineCap)2;
		Pen val2 = val;
		try
		{
			g.DrawLines(val2, pts);
		}
		finally
		{
			((IDisposable)val2)?.Dispose();
		}
		Pen val3 = new Pen(RopeFill, 1.7f);
		val3.LineJoin = (LineJoin)2;
		val3.StartCap = (LineCap)2;
		val3.EndCap = (LineCap)2;
		Pen val4 = val3;
		try
		{
			g.DrawLines(val4, pts);
		}
		finally
		{
			((IDisposable)val4)?.Dispose();
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
