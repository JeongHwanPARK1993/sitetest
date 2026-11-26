using System;
using System.Drawing;
using System.Drawing.Drawing2D;

namespace MyMascot;

public static class GraphicsExtensions
{
	public static void FillRoundedRectangle(this Graphics g, Brush brush, RectangleF rect, float radius)
	{
		GraphicsPath val = RoundedRect(rect, radius);
		try
		{
			g.FillPath(brush, val);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	public static void DrawRoundedRectangle(this Graphics g, Pen pen, RectangleF rect, float radius)
	{
		GraphicsPath val = RoundedRect(rect, radius);
		try
		{
			g.DrawPath(pen, val);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	private static GraphicsPath RoundedRect(RectangleF rect, float radius)
	{
		//IL_0000: Unknown result type (might be due to invalid IL or missing references)
		//IL_0006: Expected O, but got Unknown
		GraphicsPath val = new GraphicsPath();
		float num = radius * 2f;
		val.AddArc(rect.X, rect.Y, num, num, 180f, 90f);
		val.AddArc(rect.Right - num, rect.Y, num, num, 270f, 90f);
		val.AddArc(rect.Right - num, rect.Bottom - num, num, num, 0f, 90f);
		val.AddArc(rect.X, rect.Bottom - num, num, num, 90f, 90f);
		val.CloseFigure();
		return val;
	}
}
