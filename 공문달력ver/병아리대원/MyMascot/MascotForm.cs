using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace MyMascot;

public class MascotForm : Form
{
	private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

	private struct RECT
	{
		public int Left;

		public int Top;

		public int Right;

		public int Bottom;
	}

	internal struct POINTAPI
	{
		public int X;

		public int Y;

		public POINTAPI(int x, int y)
		{
			X = x;
			Y = y;
		}
	}

	internal struct SIZEAPI
	{
		public int cx;

		public int cy;

		public SIZEAPI(int w, int h)
		{
			cx = w;
			cy = h;
		}
	}

	internal struct BLENDFUNCTION
	{
		public byte BlendOp;

		public byte BlendFlags;

		public byte SourceConstantAlpha;

		public byte AlphaFormat;
	}

	private struct LASTINPUTINFO
	{
		public uint cbSize;

		public uint dwTime;
	}

	private const int WS_EX_LAYERED = 524288;

	private const int ULW_ALPHA = 2;

	private const byte AC_SRC_OVER = 0;

	private const byte AC_SRC_ALPHA = 1;

	private const uint SWP_NOSIZE = 1u;

	private const uint SWP_NOMOVE = 2u;

	private const uint SWP_NOACTIVATE = 16u;

	private const uint SWP_NOOWNERZORDER = 512u;

	private const double RopeDescendSpeedPxPerSec = 170.0;

	private const int Gravity = 2;

	private const int MaxFallSpeed = 16;

	private const double AirFriction = 0.995;

	private const double BounceLoss = 0.55;

	private const int PlatformsCacheMs = 300;

	private const float FallRopeTopFraction = 0.667f;

	private const float FallRopeBottomFraction = 0.781f;

	private const float UpRopeTopFraction = 0.69f;

	private const float UpRopeBottomFraction = 0.751f;

	private const float ClimbWallRightFraction = 0.965f;

	private const double FocusFadeSeconds = 2.0;

	private const int FocusHalfMinutes = 10;

	private const int RestBreakSeconds = 12;

	private static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);

	private int lastTopmostTick;

	private Timer walkTimer;

	private Timer animTimer;

	private int x;

	private int y;

	private int direction;

	private int velX;

	private int velY;

	private int frameIndex;

	private List<Image> idleFrames;

	private List<Image> walkFrames;

	private List<Image> alertFrames;

	private List<Image> flyFrames;

	private List<Image> fallFrames;

	private List<Image> carFrames;

	private List<Image> longIdleFrames;

	private List<Image> welcomeBackFrames;

	private bool isThrown;

	private bool isDriving;

	private bool longIdleActive;

	private bool deepSleepActive;

	private bool quietMode;

	private List<Image> sleepFrames;

	private List<Image> quietFrames;

	private Image[] focusImages;

	private bool focusMode;

	private DateTime focusStartTime;

	private int focusTier;

	private int focusFiveHourSubTier;

	private Image selectedFocusFrame;

	private Image selectedQuietFrame;

	private int welcomeBackTicksRemaining;

	private string alertMessage;

	private int alertTicksRemaining;

	private Image selectedAlertFrame;

	private Image selectedIdleFrame;

	private int selectedIdlePoseIndex;

	private Image runFrame;

	private bool dashActive;

	private DateTime poseStartTime;

	private Image selectedCarFrame;

	private bool selectedCarFacesRight;

	private string speechText;

	private int speechTicksRemaining;

	private static readonly string[] SaluteLines = new string[23]
	{
		"현장에서도 사무실에서도, 모두가 소중한 한 팀이에요.", "안전이 최우선, 오늘도 무사히 퇴근해요.", "당신의 하루가 누군가에겐 큰 안심이 돼요.", "오늘도 안전하게, 내일도 건강하게!", "늘 시민을 지켜 주셔서 고맙습니다.", "오늘도 무사히 마치는 게 최고의 성과예요.", "안전을 지키는 사람이 가장 안전해야 해요.", "현장에 계신 동료들도 응원해요.", "출동 없는 평온한 하루가 되길 바라요.", "당신의 헌신 덕분에 시민이 안심해요.",
		"가족에게 돌아가는 길도 안전하길 바라요.", "무리하지 마세요. 안전이 먼저예요.", "훈련은 실전처럼, 마음은 따뜻하게!", "늘 침착한 당신이 자랑스러워요.", "센터에서 사무실에서, 모두가 한마음이에요.", "우리 서 직원 모두가 영웅이에요.", "현장 활동 후엔 꼭 충분히 쉬어요.", "팀워크가 곧 안전이에요. 서로 챙겨 줘요.", "늘 최선을 다하는 당신에게 박수를 보내요.", "오늘도 시민 곁을 지켜 줘서 고마워요.",
		"야간근무 후엔 꼭 푹 쉬어요. 몸이 먼저예요.", "교대근무 하는 당신, 정말 대단해요.", "건강 꼭 챙겨요. 당신이 제일 소중해요."
	};

	private static readonly string[] MealLines = new string[4] { "식사시간이야, 맛있게 먹어~", "밥 먹을 시간! 맛점하세요", "오늘 메뉴는 뭘까? 든든하게 먹자", "밥심이지! 맛있게 드세요" };

	private static readonly string[] PositiveLines = new string[25]
	{
		"커피 한 잔의 여유, 지금이 딱 좋은 타이밍이에요.", "오늘 점심은 뭐 드셨어요? 맛있는 거 먹었길 바라요.", "일이 많아도 괜찮아요. 하나씩 지우다 보면 끝나요.", "수고한 나에게 작은 보상 하나쯤은 괜찮아요.", "웃으면 복이 와요. 지금 한 번 웃어 볼까요?", "새로운 한 주, 멋진 시작이에요.", "금요일이 코앞이에요. 조금만 더 힘내요!", "커피가 없으면 일이 안 되죠. 한 잔 하고 와요.", "키보드야, 오늘도 잘 부탁해!", "엑셀도 오늘은 당신 편이에요.",
		"회의도 웃으면서 하면 금방 끝나요.", "결재 올라간 문서, 곧 돌아올 거예요.", "마음은 느긋하게, 오늘도 여유롭게!", "오늘의 행운은 이미 당신 곁에 있어요.", "오늘도 맑음! 기분 좋은 하루예요.", "오늘은 한 걸음씩 가볍게 가요.", "칭찬받을 일 하나, 오늘도 쌓았어요.", "지금 입꼬리 한 번 올려 볼까요?", "당신 덕분에 오늘 사무실 공기가 좋아요.", "오늘 점심이 맛있으면 반은 성공이에요.",
		"작은 행복을 찾는 하루 되세요.", "오늘도 잘 해낼 당신, 응원합니다!", "기분 전환이 필요하면 저를 쓰다듬어 주세요.", "저는 항상 당신 편이에요.", "오늘도 같이 힘내 봐요!"
	};

	private static readonly string[] MorningLines = new string[10] { "좋은 아침이에요! 오늘도 천천히 시작해 봐요.", "출근하느라 수고했어요. 따뜻한 차 한 잔 어때요?", "오늘 하루도 무탈하길 응원할게요.", "아침엔 오늘 할 일 세 가지만 정해 봐요.", "시작이 반이에요. 이미 절반은 해냈어요.", "오늘의 컨디션은 어때요? 무리하지 말아요.", "새로운 하루, 새로운 기회가 기다리고 있어요.", "일찍 나온 당신, 오늘 하루 든든하게 시작해요.", "기지개 한 번 쭉 켜고 시작해 볼까요?", "오늘도 웃는 얼굴로 만나요." };

	private static readonly string[] LeaveLines = new string[21]
	{
		"퇴근이다! 오늘도 수고했어", "칼퇴 가즈아!", "내일 또 봐요!", "고생 많았어요, 조심히 가세요", "퇴근까지 얼마 안 남았어요. 조금만 힘내요!", "오늘도 고생한 당신, 퇴근길은 가볍길 바라요.", "오늘 하루 정말 고생 많았어요.", "퇴근 준비할 시간이에요. 마무리 잘해요.", "내일 할 일은 내일의 나에게 맡겨요.", "퇴근 후엔 일 생각은 잠깐 내려놓아요.",
		"집에 가면 맛있는 저녁 꼭 챙겨 먹어요.", "오늘의 나, 충분히 잘했어요.", "퇴근길 안전운전하세요.", "푹 쉬고 내일 또 웃으며 만나요.", "수고한 만큼 오늘 밤은 편안하길 바라요.", "일은 끝났어요. 이제 나를 위한 시간이에요.", "따뜻한 샤워로 하루를 개운하게 마무리해요.", "가족과 함께하는 저녁이 되길 바라요.", "하루를 잘 마무리한 당신께 박수를!", "내일은 오늘보다 조금 더 가벼울 거예요.",
		"오늘도 무사히 마친 당신, 정말 멋져요."
	};

	private static readonly string[][] IdlePoseLines = new string[16][]
	{
		new string[8] { "음... 뭐하지?", "잠깐 멈칫", "오늘 뭐 재밌는 거 없나~", "오늘은 어떤 좋은 일이 생길까?", "잠깐 하늘 한번 볼까요?", "좋은 생각만 하기!", "지금 이 순간도 소중해요", "마음이 편안해요" },
		new string[23]
		{
			"물 한 잔 마시고 오세요. 목마르면 집중도 흐려져요.", "어깨 한 번 돌리고, 스트레칭 잠깐 어때요?", "눈이 피곤하죠? 먼 곳을 20초만 바라봐요.", "식사는 거르지 말고 꼭 챙겨 드세요.", "오늘 밤은 푹 주무세요. 충분한 휴식도 업무예요.", "근무 후엔 꼭 쉬어 가요. 체력이 가장 큰 자산이에요.", "잠깐 자리에서 일어나 걸어 볼까요?", "허리 펴고 앉았나요? 바른 자세가 건강이에요.", "눈 깜빡깜빡, 화면만 보면 눈이 말라요.", "점심 후엔 가벼운 산책이 최고예요.",
			"목이 뻐근하면 고개를 천천히 돌려 줘요.", "숨 크게 들이쉬고, 천천히 내쉬어 봐요.", "오늘 물 많이 마셨나요? 한 잔 더!", "쉬는 것도 일의 일부예요. 잠깐 쉬어요.", "몸이 원하는 휴식, 잘 챙겨 줘요.", "잠깐 눈을 감고 쉬어도 좋아요.", "손목도 쉬게 해 줘요. 스트레칭 한 번!", "건강해야 일도 잘되는 거 알죠?", "달콤한 간식으로 기분 전환 어때요?", "오늘은 조금 일찍 자 볼까요?",
			"좋아하는 노래 한 곡 들어 볼까요?", "언제든 이야기해요. 제가 들을게요.", "가장 소중한 건 당신의 건강이에요."
		},
		new string[8] { "잠깐 쉴게요", "잠깐 숨 고르기~", "앉았다 갈게요", "쉬어 가도 괜찮아요", "여유를 즐기는 중이에요", "충전되면 다시 출발!", "다리도 쉬어야죠", "느긋하게 한숨 돌려요" },
		SaluteLines,
		new string[8] { "오늘 할 일 체크!", "빠진 거 없나 확인 중", "점검 완료!", "안전 점검 이상 무!", "하나씩 체크하면 금방이에요", "꼼꼼하게 확인 완료!", "준비는 철저하게!", "빠짐없이 잘 챙겼어요" },
		MealLines,
		new string[8] { "아자아자 화이팅!", "오늘도 신나게!", "좋아좋아!", "세상아 덤벼라!", "오늘도 해낼 수 있어!", "기분 최고!", "모두 모두 힘내요!", "웃으면 다 잘될 거예요!" },
		new string[10] { "오늘도 출근 완료!", "준비됐어요, 언제든 불러 주세요", "오늘 날씨 어때요?", "잠깐 숨 고르는 중이에요", "주변 이상 무!", "오늘도 함께라서 든든해요", "뭐 도와 드릴 거 없어요?", "물 한 잔 챙겨 마셔요", "오늘 하루도 차근차근!", "제가 옆에 있을게요" },
		new string[12]
		{
			"아자아자 화이팅!", "오늘도 힘차게 가 보자고!", "할 수 있다, 할 수 있어!", "기운 팍팍 넣어 드릴게요!", "오늘 컨디션 최고예요!", "좋았어, 이 기세로 쭉!", "힘내라 힘! 영차!", "신나게 일해 볼까요?", "에너지 충전 완료!", "같이 파이팅 해요!",
			"세상아 덤벼라, 내가 간다!", "오늘 하루, 내가 접수한다!"
		},
		new string[10] { "헤헤, 기분 좋다~", "같이 있어서 행복해요", "오늘 좋은 일 있을 것 같아요!", "웃는 얼굴이 제일 예뻐요", "마음이 몽글몽글해요", "고마운 일이 가득한 하루!", "당신 덕분에 웃어요", "행복은 가까이에 있어요", "오늘도 사랑스러운 하루~", "기분 좋은 바람이 불어요" },
		new string[10] { "오늘도 잘 부탁드립니다!", "수고 많으십니다", "늘 감사드려요", "공손하게 인사드려요", "도움이 됐다면 기뻐요", "오늘도 신세 많이 질게요", "부족하지만 열심히 할게요", "항상 고맙습니다", "꾸벅! 반가워요", "좋은 하루 되세요" },
		new string[10] { "최고예요!", "지금 아주 잘하고 있어요", "역시 믿고 보는 실력!", "오늘 일 처리 완벽해요", "엄지 척!", "멋진 선택이에요", "이대로만 가면 돼요", "당신이 최고야!", "칭찬 도장 꾹!", "잘했어요, 정말로!" },
		new string[10] { "충성! 오늘도 안전 근무!", "임무 완료를 향해!", "안전 점검 이상 없습니다!", "출동 준비 완료!", "시민의 안전, 우리가 지킵니다", "오늘도 무사히, 충성!", "대원 보고합니다, 모두 안전!", "든든한 동료가 되겠습니다", "현장도 사무실도 안전 제일!", "당신의 노고에 경례!" },
		new string[10] { "제 마음을 받아 주세요!", "사랑해요, 우리 대원님!", "하트 뿅뿅~", "오늘도 응원 하트 보내요", "마음까지 따뜻해지는 하루", "당신은 소중한 사람이에요", "좋아하는 마음 가득!", "하트 충전해 드릴게요", "힘들 땐 이 하트를 기억해요", "늘 고마운 마음이에요" },
		new string[10] { "어머, 벌써 시간이 이렇게?", "앗, 깜짝이야!", "우와, 대단해요!", "헉, 이걸 벌써 다 했어요?", "어머나, 멋지다!", "오잉? 무슨 일이에요?", "와, 놀라운 실력인데요?", "깜짝 선물 같은 하루예요", "어머, 반가워요!", "세상에, 최고예요!" },
		new string[13]
		{
			"좋아, 집중해서 끝내 보자!", "이번엔 꼭 해낸다!", "할 일 목록 하나씩 지우기!", "마음 단단히 먹었어요", "포기란 없다!", "끝까지 함께 가요", "오늘 목표, 반드시 달성!", "준비 완료, 시작합니다!", "자신감 충전 완료!", "한 걸음씩 꾸준히!",
			"세상아 덤벼라!", "어떤 일이든 덤벼라, 다 해낸다!", "오늘의 난관, 가볍게 넘긴다!"
		}
	};

	private static readonly string[] RunLines = new string[10] { "출동이다, 다다다다!", "잠깐만요, 금방 다녀올게요!", "빨리빨리 가 볼까!", "바람처럼 달려요~", "늦지 않게 출발!", "달리기는 자신 있어요!", "현장으로 고고!", "운동도 되고 좋다!", "슝슝~ 지나갑니다!", "기다려, 금방 갈게!" };

	private static readonly string[] WalkLines = new string[9] { "어디 가볼까?", "산책 중~", "걷는 중이에요", "오늘 날씨 좋다", "산책하기 좋은 날이에요", "천천히 걸어도 괜찮아요", "이상 없나 순찰 중!", "오늘도 한 바퀴!", "걷다 보면 기분이 좋아져요" };

	private static readonly string[] DriveLines = new string[8] { "부릉부릉!", "출동!", "타고 가요~", "오늘도 안전운전!", "현장으로 빠르게!", "길 비켜 주셔서 감사해요!", "웃음 배달 갑니다~", "목적지까지 안전하게!" };

	private static readonly string[] RopeDownLines = new string[5] { "안전하게 하강합니다!", "천천히, 안전하게~", "로프 하강 훈련 중!", "착지 준비 완료!", "안전 확인하며 내려가요" };

	private static readonly string[] RopeUpLines = new string[5] { "한 칸씩 차근차근!", "영차, 거의 다 왔다!", "높이 올라가 볼게요!", "체력 훈련도 즐겁게!", "꼭대기에서 손 흔들게요!" };

	private static readonly string[] SleepLines = new string[5] { "쿨쿨... 좋은 꿈 꿀게요", "잠깐 충전 중이에요", "푹 쉬고 올게요~", "꿈속에서도 응원해요", "돌아오면 깨워 주세요" };

	private static readonly string[] QuietLines = new string[5] { "나 좀 쉴게", "쉬는 게 좋아~", "조용히 있을게요", "잠깐 멈춰 있을래", "조용히 응원할게요" };

	private static readonly string[] FocusWorkLines = new string[26]
	{
		"한 가지씩 차근차근, 오늘도 잘 풀릴 거예요.", "당신이 있어서 우리 서가 든든해요.", "작은 일도 꼼꼼히 챙기는 당신이 최고예요.", "오늘의 한 걸음이 내일의 큰 성과가 돼요.", "어떤 업무도 멋지게 해내는 사람, 바로 당신!", "지금 이 순간도 누군가의 안전을 지키고 있어요.", "집중하는 모습이 정말 멋져요.", "지금처럼 하면 술술 풀릴 거예요.", "천천히 정확하게, 그게 최고예요.", "하나씩 차근차근 가요.",
		"차근차근 하면 다 잘될 거예요.", "문서 하나에도 정성을 담는 당신, 존경해요.", "꼼꼼함은 당신의 가장 큰 강점이에요.", "해낸 일 하나하나가 다 빛나요.", "지금 하는 일이 모여 큰 일을 만들어요.", "모르는 건 물어봐도 괜찮아요. 같이 풀면 돼요.", "서류 하나하나 멋지게 정리하고 있어요.", "여유 있게 호흡하며 가요.", "오늘 할 일의 절반은 이미 끝났을지도 몰라요.", "당신의 일처리는 믿음직해요.",
		"말없이 해내는 사람이 가장 강해요.", "당신은 늘 멋지게 해내 왔어요.", "동료들도 당신 덕분에 힘을 얻고 있어요.", "오늘의 노력은 꼭 좋은 결과로 돌아와요.", "복잡한 일도 정리하면 길이 보여요.", "지금 잘하고 있다는 신호예요. 계속 가요!"
	};

	private static readonly string[] FocusEncourageLines = new string[6] { "오늘도 수고 많으셨어요. 정말 잘하고 계세요.", "바쁜 하루 속에서도 묵묵히 해내는 당신, 멋져요.", "지금도 이미 충분히 잘하고 있어요.", "잠깐 숨 한 번 크게 쉬고 기지개 켜 봐요.", "보이지 않는 곳에서의 노력, 제가 알아요.", "오늘 해낸 일이 생각보다 훨씬 많아요." };

	private static readonly string[] ThrownLines = new string[8] { "드론 출동~!", "우와 높다!", "하늘 순찰 중~", "하늘에서 보니 더 멋져요!", "드론 비행 훈련 중!", "구름 위로 출동~", "높이 날아올라요!", "바람이 시원해요!" };

	private static readonly string[] FallLines = new string[3] { "안전제일!", "안전하게 착지!", "안전 확인 완료!" };

	private static readonly string[] ShakeLines = new string[5] { "같이 춤춰요~", "흔들흔들 신난다!", "핑글핑글 재밌다!", "리듬 타는 중~", "흔들어도 끄떡없어요!" };

	private int lastDragVelXSign;

	private int shakeFlipCount;

	private DateTime lastShakeFlipTime;

	private int speechCooldownTicks;

	private int descendX;

	private int descendFromY;

	private int descendToY;

	private int descendTick;

	private int descendTicksTotal;

	private Rectangle descendTargetPlatform;

	private int descendPhase;

	private int dropTick;

	private int dropTicksTotal;

	private Random rnd;

	private MascotState state;

	private int stateTicksRemaining;

	private double walkBobPhase;

	private Timer fxTimer;

	private int lastRedrawTick;

	private double landImpact;

	private double dragTilt;

	private int groundY;

	private Rectangle currentPlatform;

	private RopeLineForm ropeLine;

	private SpeechBubbleForm speechBubble;

	private EdgeGlowForm edgeGlow;

	private AlarmDialogForm alertDialog;

	private bool dragging;

	private Point dragOffset;

	private Point lastDragScreenPos;

	private Point dragGestureStartPos;

	private Point holdStillAnchor;

	private DateTime holdStillSince;

	private DateTime lastDragTime;

	private double dragVelX;

	private double dragVelY;

	private List<Rectangle> platformsCache;

	private DateTime platformsCacheTime;

	private List<Image> climbFrames;

	private List<Image> upFrames;

	private bool climbOnLeft;

	private int climbTick;

	private int climbTicksTotal;

	private int climbStartY;

	private int ropeUpPhase;

	private int ropeUpTick;

	private int ropeUpTicksTotal;

	private int ropeUpFromY;

	private int ropeUpToY;

	private DateTime lastWallClimb;

	private static readonly string[] ClimbLines = new string[5] { "영차영차!", "벽 타기 훈련 시작!", "높은 곳도 문제없어!", "로프 준비 완료!", "세상아 덤벼라, 올라간다!" };

	private float upTopDx;

	private float upBottomDx;

	private int upArtTop;

	private int upArtBottom;

	private float ropeTopDx;

	private float ropeBottomDx;

	private int ropeArtTop;

	private int ropeArtBottom;

	private List<Image> giftFrames;

	private Image selectedGiftFrame;

	private DateTime mouseDownTime;

	private bool giftActive;

	private DateTime giftNotBefore;

	private string giftRollDate;

	private DateTime heartBurstUntil;

	private static readonly string[] GiftLines = new string[5] { "내 선물을 받아줘!", "짜잔~ 내 선물이야!", "오늘 하루 수고한 당신께 드려요", "준비한 선물이에요, 받아 줄래요?", "마음을 담아 준비했어요" };

	private static readonly string[] GiftThanksLines = new string[10] { "좋은 하루 보내!", "오늘도 웃는 일만 가득하길!", "당신은 정말 소중한 사람이에요", "늘 응원하고 있어요, 힘내요!", "오늘도 정말 멋져요!", "행복한 일이 찾아올 거예요", "받아 줘서 고마워요!", "당신 덕분에 오늘도 든든해요", "하루 끝까지 기분 좋게 보내요!", "언제나 당신 편이에요" };

	private static readonly int[] FocusTierMinutes = new int[6] { 0, 30, 60, 120, 180, 300 };

	private Image prevFocusFrame;

	private DateTime focusFadeStart;

	private Image focusHalfImage;

	private Image restImage;

	private bool focusHalfShown;

	private DateTime restUntil;

	private Image pendingFocusFrame;

	private static readonly string[] StretchLines = new string[10] { "스트레칭 하자! 쭈욱~", "기지개 한 번 쭉 켜요!", "어깨 돌리기, 하나 둘!", "목도 살살 풀어 줘요", "잠깐 일어나서 몸 풀어요", "손목도 빙글빙글~", "허리 쭉 펴고 심호흡!", "눈도 잠깐 쉬게 해 줘요", "물 한 모금 마시고 다시 집중!", "몸이 풀리면 일도 술술 풀려요" };

	private ChoiceBubbleForm focusChoices;

	private bool endingFocus;

	private static readonly string[] KeepFocusLines = new string[5] { "좋아요, 계속 집중해 봐요!", "그래요, 조금만 더 힘내요!", "집중 모드 계속 갑니다!", "멋져요, 이 흐름 그대로!", "끝까지 함께할게요!" };

	private static readonly string[] FocusDoneLines = new string[5] { "수고했어요! 이제 좀 쉬어요~", "집중 끝! 정말 잘했어요", "오늘도 열심히 했어요, 쉬어 가요!", "잘했어요! 잠깐 산책할까요?", "고생했어요, 기지개 쭉~" };

	private DateTime nextFocusChatter;

	private Bitmap frameBuffer;

	private int lastBubbleFrontTick;

	private static readonly PointF[] FocusSteamAt = new PointF[9]
	{
		PointF.Empty,
		new PointF(0.235f, 0.57f),
		new PointF(0.2f, 0.6f),
		new PointF(0.15f, 0.5f),
		new PointF(0.18f, 0.17f),
		new PointF(0.24f, 0.11f),
		PointF.Empty,
		new PointF(0.24f, 0.06f),
		new PointF(0.25f, 0.06f)
	};

	private static readonly float[] FocusSteamRise = new float[9] { 0f, 11f, 13f, 16f, 24f, 24f, 0f, 24f, 24f };

	private static readonly Font[] ZFonts = Enumerable.Range(7, 7).Select((Func<int, Font>)((int s) => new Font("Arial", (float)s, (FontStyle)1))).ToArray();

	protected override CreateParams CreateParams
	{
		get
		{
			CreateParams createParams = base.CreateParams;
			createParams.ExStyle |= 0x80000;
			return createParams;
		}
	}

	private static double Clock => (double)Environment.TickCount / 1000.0;

	public event Action<bool> FocusModeChanged;

	[DllImport("user32.dll")]
	private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

	[DllImport("user32.dll")]
	private static extern bool IsWindowVisible(IntPtr hWnd);

	[DllImport("user32.dll")]
	private static extern bool IsIconic(IntPtr hWnd);

	[DllImport("user32.dll")]
	private static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

	[DllImport("user32.dll")]
	private static extern int GetWindowTextLength(IntPtr hWnd);

	[DllImport("user32.dll", SetLastError = true)]
	private static extern bool UpdateLayeredWindow(IntPtr hwnd, IntPtr hdcDst, ref POINTAPI pptDst, ref SIZEAPI psize, IntPtr hdcSrc, ref POINTAPI pptSrc, int crKey, ref BLENDFUNCTION pblend, int dwFlags);

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

	[DllImport("user32.dll")]
	private static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

	private void KeepOnTop()
	{
		if (ropeLine != null && ((Control)ropeLine).Visible)
		{
			SetWindowPos(((Control)ropeLine).Handle, HWND_TOPMOST, 0, 0, 0, 0, 531u);
		}
		SetWindowPos(((Control)this).Handle, HWND_TOPMOST, 0, 0, 0, 0, 531u);
		if (speechBubble != null && ((Control)speechBubble).Visible)
		{
			SetWindowPos(((Control)speechBubble).Handle, HWND_TOPMOST, 0, 0, 0, 0, 531u);
		}
		if (focusChoices != null && !((Control)focusChoices).IsDisposed && ((Control)focusChoices).Visible)
		{
			SetWindowPos(((Control)focusChoices).Handle, HWND_TOPMOST, 0, 0, 0, 0, 531u);
		}
		lastTopmostTick = Environment.TickCount;
	}

	[DllImport("user32.dll")]
	private static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);

	private static long GetSystemIdleMilliseconds()
	{
		LASTINPUTINFO plii = default(LASTINPUTINFO);
		plii.cbSize = (uint)Marshal.SizeOf(plii);
		if (!GetLastInputInfo(ref plii))
		{
			return 0L;
		}
		return (uint)(Environment.TickCount - (int)plii.dwTime);
	}

	private void TrySpeak(string[] bank)
	{
		if (speechCooldownTicks <= 0 && bank != null && bank.Length != 0)
		{
			ShowSpeech(RandomLine(bank), 3500);
		}
	}

	public MascotForm()
	{
		//IL_027d: Unknown result type (might be due to invalid IL or missing references)
		//IL_0287: Expected O, but got Unknown
		//IL_02b7: Unknown result type (might be due to invalid IL or missing references)
		//IL_02c1: Expected O, but got Unknown
		//IL_02f9: Unknown result type (might be due to invalid IL or missing references)
		//IL_0303: Expected O, but got Unknown
		//IL_0342: Unknown result type (might be due to invalid IL or missing references)
		//IL_0348: Expected O, but got Unknown
		//IL_035a: Unknown result type (might be due to invalid IL or missing references)
		//IL_0361: Expected O, but got Unknown
		//IL_0374: Unknown result type (might be due to invalid IL or missing references)
		//IL_037b: Expected O, but got Unknown
		((Form)this).StartPosition = FormStartPosition.Manual;   // 처음 띄울 때 윈도우가 위치를 바꾸지 않게 (로프 위치 어긋남 수정)
		MouseEventHandler val = null;
		MouseEventHandler val2 = null;
		MouseEventHandler val3 = null;
		direction = 1;
		idleFrames = new List<Image>();
		walkFrames = new List<Image>();
		alertFrames = new List<Image>();
		flyFrames = new List<Image>();
		fallFrames = new List<Image>();
		carFrames = new List<Image>();
		longIdleFrames = new List<Image>();
		welcomeBackFrames = new List<Image>();
		sleepFrames = new List<Image>();
		quietFrames = new List<Image>();
		focusImages = (Image[])(object)new Image[9];
		focusTier = -1;
		focusFiveHourSubTier = -1;
		alertMessage = "";
		selectedIdlePoseIndex = -1;
		poseStartTime = DateTime.Now;
		selectedCarFacesRight = true;
		speechText = "";
		lastShakeFlipTime = DateTime.MinValue;
		rnd = new Random();
		currentPlatform = Rectangle.Empty;
		dragOffset = Point.Empty;
		lastDragScreenPos = Point.Empty;
		dragGestureStartPos = Point.Empty;
		holdStillAnchor = Point.Empty;
		holdStillSince = DateTime.Now;
		lastDragTime = DateTime.Now;
		platformsCacheTime = DateTime.MinValue;
		climbFrames = new List<Image>();
		upFrames = new List<Image>();
		lastWallClimb = DateTime.MinValue;
		giftFrames = new List<Image>();
		mouseDownTime = DateTime.MinValue;
		giftNotBefore = DateTime.MaxValue;
		giftRollDate = "";
		heartBurstUntil = DateTime.MinValue;
		focusFadeStart = DateTime.MinValue;
		restUntil = DateTime.MinValue;
		nextFocusChatter = DateTime.MaxValue;
		((Form)this).FormBorderStyle = (FormBorderStyle)0;
		((Form)this).ShowInTaskbar = false;
		((Form)this).TopMost = true;
		((Control)this).Width = 140;
		((Control)this).Height = 140;
		Rectangle workingArea = Screen.PrimaryScreen.WorkingArea;
		x = workingArea.Left + rnd.Next(0, Math.Max(1, workingArea.Width - ((Control)this).Width));
		y = workingArea.Top + rnd.Next(0, Math.Max(1, workingArea.Height - ((Control)this).Height));
		((Form)this).Location = new Point(x, y);
		LoadImages();
		if (!StartRopeDescent())
		{
			EnterState(MascotState.Airborne);
		}
		RedrawNow();
		walkTimer = new Timer();
		walkTimer.Interval = 40;
		walkTimer.Tick += WalkTick;
		walkTimer.Start();
		animTimer = new Timer();
		animTimer.Interval = 320;
		animTimer.Tick += delegate
		{
			frameIndex++;
			RedrawNow();
		};
		animTimer.Start();
		fxTimer = new Timer();
		fxTimer.Interval = 66;
		fxTimer.Tick += delegate
		{
			if (((Control)this).Visible)
			{
				if (landImpact > 0.0)
				{
					landImpact = Math.Max(0.0, landImpact - 0.16);
				}
				if (Environment.TickCount - lastRedrawTick >= 60)
				{
					RedrawNow();
				}
				if (!dragging && Environment.TickCount - lastTopmostTick >= 1000)
				{
					KeepOnTop();
				}
			}
		};
		fxTimer.Start();
		if (val == null)
		{
			val = (MouseEventHandler)delegate(object s, MouseEventArgs e)
			{
				//IL_0001: Unknown result type (might be due to invalid IL or missing references)
				//IL_000b: Invalid comparison between Unknown and I4
				if ((int)e.Button == 1048576)
				{
					dragging = true;
					dragOffset = e.Location;
					lastDragScreenPos = Control.MousePosition;
					lastDragTime = DateTime.Now;
					dragGestureStartPos = Control.MousePosition;
					mouseDownTime = DateTime.Now;
					holdStillAnchor = Control.MousePosition;
					holdStillSince = DateTime.Now;
					dragVelX = 0.0;
					dragVelY = 0.0;
					lastDragVelXSign = 0;
					shakeFlipCount = 0;
					if (ropeLine != null)
					{
						((Control)ropeLine).Hide();
					}
				}
			};
		}
		((Control)this).MouseDown += val;
		if (val2 == null)
		{
			val2 = (MouseEventHandler)delegate(object s, MouseEventArgs e)
			{
				if (dragging)
				{
					((Form)this).Location = new Point(((Form)this).Location.X + e.X - dragOffset.X, ((Form)this).Location.Y + e.Y - dragOffset.Y);
					x = ((Form)this).Location.X;
					y = ((Form)this).Location.Y;
					DateTime now = DateTime.Now;
					Point mousePosition = Control.MousePosition;
					double totalSeconds = (now - lastDragTime).TotalSeconds;
					if (totalSeconds > 0.01)
					{
						dragVelX = (double)(mousePosition.X - lastDragScreenPos.X) / totalSeconds;
						dragVelY = (double)(mousePosition.Y - lastDragScreenPos.Y) / totalSeconds;
						lastDragScreenPos = mousePosition;
						lastDragTime = now;
						if (Math.Abs(dragVelX) > 180.0)
						{
							int num = ((!(dragVelX < 0.0)) ? 1 : (-1));
							if (lastDragVelXSign != 0 && num != lastDragVelXSign)
							{
								if ((now - lastShakeFlipTime).TotalMilliseconds < 700.0)
								{
									shakeFlipCount++;
								}
								else
								{
									shakeFlipCount = 1;
								}
								lastShakeFlipTime = now;
								if (shakeFlipCount >= 3)
								{
									TrySpeak(ShakeLines);
									shakeFlipCount = 0;
								}
							}
							lastDragVelXSign = num;
						}
					}
					if (speechTicksRemaining > 0)
					{
						UpdateSpeechBubble();
					}
				}
			};
		}
		((Control)this).MouseMove += val2;
		if (val3 == null)
		{
			val3 = (MouseEventHandler)delegate(object s, MouseEventArgs e)
			{
				//IL_001f: Unknown result type (might be due to invalid IL or missing references)
				//IL_0029: Invalid comparison between Unknown and I4
				bool talkClick = false;
				if (dragging && !giftActive && !focusMode && (int)e.Button == 1048576)
				{
					Point mp = Control.MousePosition;
					int ddx = mp.X - dragGestureStartPos.X;
					int ddy = mp.Y - dragGestureStartPos.Y;
					talkClick = ddx * ddx + ddy * ddy <= 36 && (DateTime.Now - mouseDownTime).TotalMilliseconds < 600.0;
				}
				if (talkClick)
				{
					((Control)this).BeginInvoke((Action)OpenTalkBox);   // 놓기 처리가 끝난 뒤 '무슨 할 말 있어요?'
				}
				if (dragging && (giftActive || focusMode) && (int)e.Button == 1048576)
				{
					Point mousePosition = Control.MousePosition;
					int num = mousePosition.X - dragGestureStartPos.X;
					int num2 = mousePosition.Y - dragGestureStartPos.Y;
					if (num * num + num2 * num2 <= 36 && (DateTime.Now - mouseDownTime).TotalMilliseconds < 600.0)
					{
						dragging = false;
						if (giftActive)
						{
							OnGiftClicked();
						}
						else
						{
							ToggleFocusChoices();
						}
						return;
					}
				}
				if (dragging)
				{
					dragging = false;
					CloseFocusChoices();
					if (ropeLine != null)
					{
						((Control)ropeLine).Hide();
					}
					double num3 = Math.Sqrt(dragVelX * dragVelX + dragVelY * dragVelY);
					int num4 = lastDragScreenPos.X - dragGestureStartPos.X;
					int value = lastDragScreenPos.Y - dragGestureStartPos.Y;
					if (Math.Abs(num4) >= 80 && Math.Abs(num4) > 2 * Math.Abs(value) && num3 < 1500.0 && carFrames.Count > 0)
					{
						Rectangle workingArea2 = Screen.FromPoint(new Point(x + ((Control)this).Width / 2, y + ((Control)this).Height / 2)).WorkingArea;
						currentPlatform = new Rectangle(workingArea2.Left, workingArea2.Bottom, workingArea2.Width, 4);
						groundY = currentPlatform.Top - ((Control)this).Height;
						y = groundY;
						((Form)this).Location = new Point(x, y);
						isThrown = false;
						StartDriving((num4 >= 0) ? 1 : (-1));
					}
					else if (num3 > 250.0)
					{
						double num5 = 0.04;
						double num6 = dragVelX * num5;
						double num7 = dragVelY * num5;
						double num8 = 30.0;
						double num9 = Math.Sqrt(num6 * num6 + num7 * num7);
						if (num9 > num8)
						{
							num6 = num6 / num9 * num8;
							num7 = num7 / num9 * num8;
						}
						velX = (int)Math.Round(num6);
						velY = (int)Math.Round(num7);
						isThrown = true;
						EnterState(MascotState.Airborne);
					}
					else
					{
						Rectangle? rectangle = FindSupportingPlatform();
						if (rectangle.HasValue)
						{
							currentPlatform = rectangle.Value;
							groundY = currentPlatform.Top - ((Control)this).Height;
							y = groundY;
							((Form)this).Location = new Point(x, y);
							velX = 0;
							velY = 0;
							isDriving = false;
							EnterState(MascotState.Walking);
						}
						else
						{
							velX = 0;
							velY = 0;
							if (!StartRopeDescent())
							{
								isThrown = false;
								EnterState(MascotState.Airborne);
							}
						}
					}
				}
			};
		}
		((Control)this).MouseUp += val3;
	}

	private List<Image> LoadFrameSet(string prefix)
	{
		List<Image> list = new List<Image>();
		for (int i = 1; i <= 30; i++)
		{
			Image val = TryLoad(prefix + i + ".png");
			if (val == null)
			{
				break;
			}
			list.Add(val);
		}
		if (list.Count == 0)
		{
			Image val2 = TryLoad(prefix + ".png");
			if (val2 != null)
			{
				list.Add(val2);
			}
		}
		return list;
	}

	private void LoadImages()
	{
		idleFrames = LoadFrameSet("idle");
		walkFrames = LoadFrameSet("walk");
		alertFrames = LoadFrameSet("alert");
		flyFrames = LoadFrameSet("fly");
		fallFrames = LoadFrameSet("fall");
		carFrames = LoadFrameSet("car");
		sleepFrames = LoadFrameSet("sleep");
		quietFrames = LoadFrameSet("quiet");
		for (int i = 1; i <= 8; i++)
		{
			focusImages[i] = TryLoad("focus" + i + ".png");
		}
		giftFrames = LoadFrameSet("gift");
		focusHalfImage = TryLoad("focus1.5.png");
		restImage = TryLoad("rest1.png");
		climbFrames = LoadFrameSet("climb");
		upFrames = LoadFrameSet("up");
		List<Image> list = LoadFrameSet("pose");
		if (idleFrames.Count == 7)
		{
			for (int j = 0; j < Math.Min(9, list.Count); j++)
			{
				idleFrames.Add(list[j]);
			}
		}
		if (list.Count >= 10)
		{
			runFrame = list[9];
		}
		if (idleFrames.Count >= 3)
		{
			longIdleFrames.Add(idleFrames[2]);
		}
		if (idleFrames.Count >= 4)
		{
			welcomeBackFrames.Add(idleFrames[3]);
		}
	}

	private static Image TryLoad(string resourceName)
	{
		//IL_001d: Unknown result type (might be due to invalid IL or missing references)
		//IL_0023: Expected O, but got Unknown
		try
		{
			Assembly executingAssembly = Assembly.GetExecutingAssembly();
			using Stream stream = executingAssembly.GetManifestResourceStream(resourceName);
			if (stream == null)
			{
				return null;
			}
			Image val = Image.FromStream(stream);
			try
			{
				return (Image)new Bitmap(val);
			}
			finally
			{
				((IDisposable)val)?.Dispose();
			}
		}
		catch
		{
			return null;
		}
	}

	private List<Rectangle> GetPlatforms()
	{
		if (platformsCache != null && (DateTime.Now - platformsCacheTime).TotalMilliseconds < 300.0)
		{
			return platformsCache;
		}
		List<Rectangle> list = new List<Rectangle>();
		IntPtr self = ((Control)this).Handle;
		EnumWindows(delegate(IntPtr hWnd, IntPtr lParam)
		{
			if (hWnd == self)
			{
				return true;
			}
			if (!IsWindowVisible(hWnd))
			{
				return true;
			}
			if (IsIconic(hWnd))
			{
				return true;
			}
			if (GetWindowTextLength(hWnd) == 0)
			{
				return true;
			}
			if (GetWindowRect(hWnd, out var lpRect))
			{
				int num2 = lpRect.Right - lpRect.Left;
				int num3 = lpRect.Bottom - lpRect.Top;
				if (num2 > 60 && num3 > 40)
				{
					list.Add(new Rectangle(lpRect.Left, lpRect.Top, num2, num3));
				}
			}
			return true;
		}, IntPtr.Zero);
		Screen[] allScreens = Screen.AllScreens;
		foreach (Screen val in allScreens)
		{
			Rectangle workingArea = val.WorkingArea;
			list.Add(new Rectangle(workingArea.Left, workingArea.Bottom, workingArea.Width, 4));
		}
		platformsCache = list;
		platformsCacheTime = DateTime.Now;
		return list;
	}

	private Rectangle? FindSupportingPlatform()
	{
		int num = y + ((Control)this).Height;
		int num2 = x + ((Control)this).Width / 2;
		Rectangle? result = null;
		int num3 = int.MaxValue;
		foreach (Rectangle platform in GetPlatforms())
		{
			if (num2 >= platform.Left && num2 <= platform.Right)
			{
				int num4 = Math.Abs(platform.Top - num);
				if (num4 <= 6 && num4 < num3)
				{
					result = platform;
					num3 = num4;
				}
			}
		}
		return result;
	}

	private Rectangle? FindCrossedPlatform(int centerX, int prevFeetY, int newFeetY)
	{
		Rectangle? result = null;
		int num = int.MaxValue;
		foreach (Rectangle platform in GetPlatforms())
		{
			if (centerX >= platform.Left && centerX <= platform.Right && platform.Top >= prevFeetY - 2 && platform.Top <= newFeetY + 2 && platform.Top < num)
			{
				result = platform;
				num = platform.Top;
			}
		}
		return result;
	}

	private bool IsFloor(Rectangle p)
	{
		return p.Height <= 4;
	}

	private Rectangle? FindAdjacentFloor(Rectangle current, bool goingRight)
	{
		Rectangle? result = null;
		int num = int.MaxValue;
		foreach (Rectangle platform in GetPlatforms())
		{
			if (IsFloor(platform) && (platform.Left != current.Left || platform.Right != current.Right))
			{
				int num2 = (goingRight ? Math.Abs(platform.Left - current.Right) : Math.Abs(platform.Right - current.Left));
				if (num2 <= 4 && num2 < num)
				{
					result = platform;
					num = num2;
				}
			}
		}
		return result;
	}

	private bool TryStartEdgeCrossing()
	{
		if (!IsFloor(currentPlatform))
		{
			return false;
		}
		bool flag = velX > 0 || (velX == 0 && direction > 0);
		Rectangle? rectangle = FindAdjacentFloor(currentPlatform, flag);
		if (!rectangle.HasValue)
		{
			if (TryStartWallClimb(flag))
			{
				return true;
			}
			velX = -velX;
			direction = -direction;
			x = Math.Max(currentPlatform.Left - ((Control)this).Width / 2, Math.Min(x, currentPlatform.Right - ((Control)this).Width / 2));
			((Form)this).Location = new Point(x, y);
			return true;
		}
		currentPlatform = rectangle.Value;
		groundY = currentPlatform.Top - ((Control)this).Height;
		y = groundY;
		((Form)this).Location = new Point(x, y);
		return true;
	}

	private void FallRopeGeometry(out float topX, out float bottomX, out int artTop, out int artBottom)
	{
		ArtRopeGeometry(fallFrames[0], 0.667f, 0.781f, out topX, out bottomX, out artTop, out artBottom);
	}

	private void ArtRopeGeometry(Image img, float topFraction, float bottomFraction, out float topX, out float bottomX, out int artTop, out int artBottom)
	{
		int num = ((Control)this).Width - 20;
		int num2 = 100;
		float num3 = (float)img.Width / (float)img.Height;
		int num4 = num;
		int num5 = (int)((float)num / num3);
		if (num5 > num2)
		{
			num5 = num2;
			num4 = (int)((float)num2 * num3);
		}
		int num6 = 10 + (num - num4) / 2;
		artBottom = 138;
		artTop = artBottom - num5;
		topX = (float)num6 + topFraction * (float)num4;
		bottomX = (float)num6 + bottomFraction * (float)num4;
	}

	private bool TryStartWallClimb(bool rightEdge)
	{
		if (climbFrames.Count == 0 || upFrames.Count == 0 || fallFrames.Count == 0)
		{
			return false;
		}
		if (quietMode || focusMode || deepSleepActive || longIdleActive || giftActive || isDriving)
		{
			return false;
		}
		if ((DateTime.Now - lastWallClimb).TotalMinutes < 5.0)
		{
			return false;
		}
		if (rnd.NextDouble() > 0.5)
		{
			return false;
		}
		lastWallClimb = DateTime.Now;
		Rectangle workingArea = Screen.FromPoint(new Point(x + ((Control)this).Width / 2, y + ((Control)this).Height / 2)).WorkingArea;
		climbOnLeft = !rightEdge;
		ArtRopeGeometry(climbFrames[0], 0.965f, 0.965f, out var topX, out var _, out var _, out var _);
		int num = (int)Math.Round(topX);
		x = (rightEdge ? (workingArea.Right - num) : (workingArea.Left - (((Control)this).Width - num)));
		y = groundY;
		climbStartY = y;
		((Form)this).Location = new Point(x, y);
		velX = 0;
		velY = 0;
		climbTick = 0;
		climbTicksTotal = Ticks(2400);
		state = MascotState.Climbing;
		frameIndex = 0;
		TrySpeak(ClimbLines);
		RedrawNow();
		return true;
	}

	private void DrawRopeUpAroundCharacter(double upFraction, double whip)
	{
		if (ropeLine != null)
		{
			int num = y + upArtTop - ((Control)ropeLine).Top;
			int gapBottom = num + (upArtBottom - upArtTop);
			ropeLine.DrawRopeUp(upFraction, whip, num, gapBottom, ((Control)ropeLine).Height, upTopDx, upBottomDx);
		}
	}

	private void TickWallClimb()
	{
		Rectangle workingArea = Screen.FromPoint(new Point(x + ((Control)this).Width / 2, climbStartY + ((Control)this).Height / 2)).WorkingArea;
		if (state == MascotState.Climbing)
		{
			climbTick++;
			y = climbStartY - frameIndex % 2 * 2;
			if (climbTick >= climbTicksTotal)
			{
				ArtRopeGeometry(upFrames[0], 0.69f, 0.751f, out var topX, out var bottomX, out upArtTop, out upArtBottom);
				float num = (topX + bottomX) / 2f;
				upTopDx = topX - num;
				upBottomDx = bottomX - num;
				y = climbStartY;
				ropeUpFromY = y;
				ropeUpToY = workingArea.Top - upArtTop;
				if (ropeLine == null)
				{
					ropeLine = new RopeLineForm();
				}
				ropeLine.PlaceAt(x + (int)Math.Round(num), workingArea.Top, y + upArtBottom);
				ropeUpPhase = 1;
				ropeUpTick = 0;
				int num2 = Math.Max(1, ropeUpFromY - ropeUpToY);
				ropeUpTicksTotal = Ticks(Math.Max(300, Math.Min(700, num2 / 2)));
				DrawRopeUpAroundCharacter(0.0, 1.0);
				((Control)ropeLine).Show();
				state = MascotState.RopeClimbing;
				frameIndex = 0;
			}
		}
		else if (ropeUpPhase == 1)
		{
			ropeUpTick++;
			double num3 = Math.Min(1.0, (double)ropeUpTick / (double)ropeUpTicksTotal);
			DrawRopeUpAroundCharacter(1.0 - Math.Pow(1.0 - num3, 3.0), 1.0);
			if (num3 >= 1.0)
			{
				ropeUpPhase = 2;
				ropeUpTick = 0;
				int num4 = Math.Max(1, ropeUpFromY - ropeUpToY);
				ropeUpTicksTotal = Ticks(Math.Max(1000, Math.Min(4500, num4 * 1000 / 110)));
				frameIndex = 0;
				TrySpeak(RopeUpLines);
			}
		}
		else
		{
			ropeUpTick++;
			double num5 = Math.Min(1.0, (double)ropeUpTick / (double)ropeUpTicksTotal);
			int num6 = ropeUpFromY - ropeUpToY;
			double num7 = Math.Max(2.0, Math.Round((double)num6 / 45.0));
			double num8 = num5 - Math.Sin(Math.PI * 2.0 * num7 * num5) / (Math.PI * 2.0 * num7);
			y = (int)((double)ropeUpFromY - (double)num6 * num8);
			DrawRopeUpAroundCharacter(1.0, Math.Max(0.0, 0.5 - num5 * 2.0));
			if (num5 >= 1.0)
			{
				y = ropeUpToY;
				((Form)this).Location = new Point(x, y);
				ropeUpPhase = 0;
				if (!StartRopeDescent())
				{
					isThrown = false;
					EnterState(MascotState.Airborne);
				}
				RedrawNow();
				return;
			}
		}
		((Form)this).Location = new Point(x, y);
		((Control)this).BringToFront();
		RedrawNow();
	}

	private void DrawRopeAroundCharacter(double visibleFraction, double whip)
	{
		if (ropeLine != null)
		{
			int num = y + ropeArtTop - ((Control)ropeLine).Top;
			ropeLine.DrawRope(visibleFraction, whip, num, num + (ropeArtBottom - ropeArtTop), ropeTopDx, ropeBottomDx);
		}
	}

	private void CheckHoldStillTrigger()
	{
		Point mousePosition = Control.MousePosition;
		int num = mousePosition.X - holdStillAnchor.X;
		int num2 = mousePosition.Y - holdStillAnchor.Y;
		if (num * num + num2 * num2 > 100)
		{
			holdStillAnchor = mousePosition;
			holdStillSince = DateTime.Now;
		}
		else if ((DateTime.Now - holdStillSince).TotalSeconds >= 3.0)
		{
			StartHeldRopeDescent();
		}
	}

	private bool StartHeldRopeDescent()
	{
		return StartRopeDescent();
	}

	private bool StartRopeDescent()
	{
		if (fallFrames.Count == 0)
		{
			return false;
		}
		int num = x + ((Control)this).Width / 2;
		int num2 = y + ((Control)this).Height;
		Rectangle? rectangle = null;
		foreach (Rectangle platform in GetPlatforms())
		{
			if (num >= platform.Left && num <= platform.Right && platform.Top >= num2 - 2 && (!rectangle.HasValue || platform.Top < rectangle.Value.Top))
			{
				rectangle = platform;
			}
		}
		if (!rectangle.HasValue)
		{
			Rectangle workingArea = Screen.FromPoint(new Point(num, y + ((Control)this).Height / 2)).WorkingArea;
			rectangle = new Rectangle(workingArea.Left, workingArea.Bottom, workingArea.Width, 4);
		}
		int num3 = rectangle.Value.Top - ((Control)this).Height;
		int num4 = num3 - y;
		if (num4 < 30)
		{
			return false;
		}
		dragging = false;
		descendX = x;
		descendFromY = y;
		descendToY = num3;
		descendTargetPlatform = rectangle.Value;
		descendPhase = 1;
		dropTick = 0;
		dropTicksTotal = Ticks(Math.Max(300, Math.Min(700, (int)((double)num4 * 0.5))));
		descendTick = 0;
		descendTicksTotal = Ticks(Math.Max(800, Math.Min(3500, (int)((double)num4 / 170.0 * 1000.0))));
		isDriving = false;
		isThrown = false;
		state = MascotState.RopeDescending;
		frameIndex = 0;
		if (!focusMode)
		{
			TrySpeak(RopeDownLines);
		}
		FallRopeGeometry(out var topX, out var bottomX, out ropeArtTop, out ropeArtBottom);
		float num5 = (topX + bottomX) / 2f;
		ropeTopDx = topX - num5;
		ropeBottomDx = bottomX - num5;
		if (ropeLine == null)
		{
			ropeLine = new RopeLineForm();
		}
		ropeLine.PlaceAt(descendX + (int)Math.Round(num5), descendFromY + ropeArtTop, descendToY + ropeArtBottom);
		DrawRopeAroundCharacter(0.0, 1.0);
		((Control)ropeLine).Show();
		((Control)this).BringToFront();
		RedrawNow();
		return true;
	}

	private void CheckSystemIdle()
	{
		CheckFocusMode();
		long systemIdleMilliseconds = GetSystemIdleMilliseconds();
		bool flag = systemIdleMilliseconds >= 600000;
		bool flag2 = sleepFrames.Count > 0 && systemIdleMilliseconds >= 3600000;
		if (flag2 && !deepSleepActive)
		{
			deepSleepActive = true;
			if (state == MascotState.Idle || state == MascotState.Walking)
			{
				EnterState(MascotState.Idle);
			}
			if (!focusMode && !quietMode)
			{
				ShowSpeech(RandomLine(SleepLines), 5000);
			}
		}
		else if (!flag2 && deepSleepActive)
		{
			deepSleepActive = false;
			welcomeBackTicksRemaining = Ticks(2500);
			if (speechCooldownTicks <= 0 && !focusMode)
			{
				ShowSpeech(RandomLine(SaluteLines), 2500);
			}
		}
		if (flag && !longIdleActive)
		{
			longIdleActive = true;
			if (state == MascotState.Idle || state == MascotState.Walking)
			{
				EnterState(MascotState.Idle);
			}
		}
		else if (!flag && longIdleActive)
		{
			longIdleActive = false;
			if (!deepSleepActive)
			{
				welcomeBackTicksRemaining = Ticks(2500);
				if (speechCooldownTicks <= 0 && !focusMode)
				{
					ShowSpeech(RandomLine(SaluteLines), 2500);
				}
			}
		}
		if (welcomeBackTicksRemaining > 0)
		{
			welcomeBackTicksRemaining--;
		}
		if (speechTicksRemaining > 0)
		{
			speechTicksRemaining--;
		}
		if (speechCooldownTicks > 0)
		{
			speechCooldownTicks--;
		}
	}

	private void StartDriving(int dragDirection)
	{
		if (carFrames.Count == 0)
		{
			return;
		}
		if (focusMode)
		{
			EnterState(MascotState.Idle);
			return;
		}
		bool flag = dragDirection > 0;
		int num = 0;
		if (carFrames.Count > 1)
		{
			num = ((!flag) ? 1 : 0);
		}
		selectedCarFrame = carFrames[num];
		selectedCarFacesRight = carFrames.Count <= 1 || num == 0;
		direction = dragDirection;
		isDriving = true;
		velX = direction * 5;
		velY = 0;
		walkBobPhase = 0.0;
		stateTicksRemaining = Ticks(rnd.Next(6000, 12000));
		state = MascotState.Walking;
		frameIndex = 0;
		TrySpeak(DriveLines);
		RedrawNow();
	}

	private void EnterState(MascotState newState)
	{
		if (focusMode && newState == MascotState.Walking)
		{
			newState = MascotState.Idle;
			isDriving = false;
			velX = 0;
			velY = 0;
		}
		if ((state == MascotState.Airborne || state == MascotState.RopeDescending) && newState != MascotState.Airborne && newState != MascotState.RopeDescending)
		{
			landImpact = 1.0;
		}
		state = newState;
		frameIndex = 0;
		giftActive = false;
		dashActive = false;
		poseStartTime = DateTime.Now;
		switch (newState)
		{
		case MascotState.Idle:
		{
			stateTicksRemaining = Ticks(rnd.Next(3500, 6000));
			int num = ((idleFrames.Count > 0) ? rnd.Next(idleFrames.Count) : (-1));
			selectedIdleFrame = ((num >= 0) ? idleFrames[num] : null);
			selectedIdlePoseIndex = num;
			if (!longIdleActive && !focusMode && !quietMode && num >= 0 && num < IdlePoseLines.Length)
			{
				string[] bank = ((rnd.NextDouble() < 0.3) ? GeneralBankForNow() : IdlePoseLines[num]);
				TrySpeak(bank);
			}
			break;
		}
		case MascotState.Walking:
			direction = ((rnd.Next(0, 2) != 0) ? 1 : (-1));
			isDriving = false;
			velY = 0;
			walkBobPhase = 0.0;
			if (runFrame != null && rnd.NextDouble() < 0.06)
			{
				dashActive = true;
				TrySpeak(RunLines);
				velX = direction * 5;
				stateTicksRemaining = Ticks(rnd.Next(2000, 2800));
			}
			else
			{
				TrySpeak(WalkLines);
				velX = direction * 2;
				stateTicksRemaining = Ticks(rnd.Next(6000, 12000));
			}
			break;
		case MascotState.Airborne:
			TrySpeak(isThrown ? ThrownLines : FallLines);
			break;
		}
	}

	private int Ticks(int milliseconds)
	{
		return Math.Max(1, milliseconds / 40);
	}

	private bool TryStartGift()
	{
		if (giftFrames.Count == 0 || quietMode || focusMode || deepSleepActive || longIdleActive)
		{
			return false;
		}
		string text = DateTime.Now.ToString("yyyy-MM-dd");
		if (AppSettings.LastGiftDate == text)
		{
			return false;
		}
		if (giftRollDate != text)
		{
			giftRollDate = text;
			giftNotBefore = DateTime.Now.AddMinutes(rnd.Next(20, 180));
		}
		if (DateTime.Now < giftNotBefore)
		{
			return false;
		}
		AppSettings.LastGiftDate = text;
		AppSettings.Save();
		EnterState(MascotState.Idle);
		velX = 0;
		selectedGiftFrame = giftFrames[rnd.Next(giftFrames.Count)];
		giftActive = true;
		stateTicksRemaining = Ticks(20000);
		ShowSpeech(RandomLine(GiftLines), 8000);
		RedrawNow();
		return true;
	}

	private void OnGiftClicked()
	{
		ShowSpeech(RandomLine(GiftThanksLines), 6000);
		heartBurstUntil = DateTime.Now.AddMilliseconds(1600.0);
		stateTicksRemaining = Ticks(5000);
	}

	private void WalkTick(object sender, EventArgs e)
	{
		if (dragging)
		{
			CheckHoldStillTrigger();
			return;
		}
		CheckSystemIdle();
		if (state == MascotState.Alerting)
		{
			alertTicksRemaining--;
			if (alertTicksRemaining <= 0)
			{
				if (edgeGlow != null)
				{
					edgeGlow.HideGlow();
				}
				if (alertDialog != null)
				{
					((Form)alertDialog).Close();
					alertDialog = null;
				}
				EnterState(MascotState.Idle);
			}
			RedrawNow();
			return;
		}
		Rectangle virtualScreen = SystemInformation.VirtualScreen;
		if (state == MascotState.Airborne)
		{
			int prevFeetY = y + ((Control)this).Height;
			x += velX;
			velY += 2;
			if (velY > 16)
			{
				velY = 16;
			}
			y += velY;
			velX = (int)((double)velX * 0.995);
			int centerX = x + ((Control)this).Width / 2;
			Rectangle? rectangle = ((velY >= 0) ? FindCrossedPlatform(centerX, prevFeetY, y + ((Control)this).Height) : ((Rectangle?)null));
			if (rectangle.HasValue)
			{
				y = rectangle.Value.Top - ((Control)this).Height;
				if (Math.Abs(velY) <= 8)
				{
					currentPlatform = rectangle.Value;
					groundY = y;
					((Form)this).Location = new Point(x, y);
					EnterState(MascotState.Walking);
					RedrawNow();
					return;
				}
				velY = -(int)((double)velY * 0.55);
				velX = (int)((double)velX * 0.7);
			}
			if (x < virtualScreen.Left)
			{
				x = virtualScreen.Left;
				velX = -velX;
			}
			if (x + ((Control)this).Width > virtualScreen.Right)
			{
				x = virtualScreen.Right - ((Control)this).Width;
				velX = -velX;
			}
			if (y < virtualScreen.Top)
			{
				y = virtualScreen.Top;
				velY = 0;
			}
			if (y > virtualScreen.Bottom + 200)
			{
				Rectangle workingArea = Screen.PrimaryScreen.WorkingArea;
				x = workingArea.Left + rnd.Next(0, Math.Max(1, workingArea.Width - ((Control)this).Width));
				y = workingArea.Top;
				velX = 0;
				velY = 0;
				((Form)this).Location = new Point(x, y);
				RedrawNow();
			}
			else
			{
				direction = ((velX < 0) ? (-1) : ((velX > 0) ? 1 : direction));
				((Form)this).Location = new Point(x, y);
				RedrawNow();
			}
		}
		else if (state == MascotState.Climbing || state == MascotState.RopeClimbing)
		{
			TickWallClimb();
		}
		else if (state == MascotState.RopeDescending)
		{
			x = descendX;
			y = descendFromY;
			if (descendPhase == 1)
			{
				dropTick++;
				frameIndex = ((fallFrames.Count > 0) ? (dropTick / 9 % fallFrames.Count) : 0);
				double num = Math.Min(1.0, (double)dropTick / (double)dropTicksTotal);
				double visibleFraction = 1.0 - Math.Pow(1.0 - num, 3.0);
				DrawRopeAroundCharacter(visibleFraction, 1.0);
				if (num >= 1.0)
				{
					descendPhase = 2;
					descendTick = 0;
				}
			}
			else
			{
				descendTick++;
				frameIndex = ((fallFrames.Count > 0) ? (descendTick / 9 % fallFrames.Count) : 0);
				double num2 = Math.Min(1.0, (double)descendTick / (double)descendTicksTotal);
				double num3 = num2 * num2 * (3.0 - 2.0 * num2);
				y = (int)((double)descendFromY + (double)(descendToY - descendFromY) * num3);
				DrawRopeAroundCharacter(1.0, Math.Max(0.0, 0.6 - num2 * 1.5));
				if (num2 >= 1.0)
				{
					currentPlatform = descendTargetPlatform;
					groundY = descendToY;
					if (ropeLine != null)
					{
						ropeLine.RetractAndHide();
					}
					EnterState(MascotState.Walking);
				}
			}
			((Form)this).Location = new Point(x, y);
			((Control)this).BringToFront();
			RedrawNow();
		}
		else if (state == MascotState.Walking)
		{
			if (x + ((Control)this).Width / 2 < currentPlatform.Left || x + ((Control)this).Width / 2 > currentPlatform.Right)
			{
				if (!TryStartEdgeCrossing() && !StartRopeDescent())
				{
					isThrown = false;
					EnterState(MascotState.Airborne);
				}
				RedrawNow();
				return;
			}
			x += velX;
			if (x + ((Control)this).Width / 2 < currentPlatform.Left || x + ((Control)this).Width / 2 > currentPlatform.Right)
			{
				if (!TryStartEdgeCrossing() && !StartRopeDescent())
				{
					isThrown = false;
					EnterState(MascotState.Airborne);
				}
				RedrawNow();
				return;
			}
			int num4 = 0;
			if (!isDriving)
			{
				walkBobPhase += (dashActive ? 0.6 : 0.35);
				num4 = (int)(Math.Abs(Math.Sin(walkBobPhase)) * 4.0);
			}
			((Form)this).Location = new Point(x, groundY - num4);
			if (velX != 0)
			{
				direction = ((velX >= 0) ? 1 : (-1));
			}
			stateTicksRemaining--;
			if (stateTicksRemaining > 0 || isDriving || !TryStartGift())
			{
				if (stateTicksRemaining <= 0)
				{
					EnterState((!(rnd.NextDouble() < 0.35)) ? MascotState.Walking : MascotState.Idle);
				}
				RedrawNow();
			}
		}
		else
		{
			if (state != MascotState.Idle)
			{
				return;
			}
			if (!FindSupportingPlatform().HasValue)
			{
				if (!StartRopeDescent())
				{
					isThrown = false;
					EnterState(MascotState.Airborne);
				}
				RedrawNow();
			}
			else if (giftActive || (!longIdleActive && !deepSleepActive && !quietMode && !focusMode))
			{
				stateTicksRemaining--;
				if (stateTicksRemaining <= 0)
				{
					EnterState(MascotState.Walking);
				}
			}
		}
	}

	public void SetQuietMode(bool on)
	{
		quietMode = on;
		if (on)
		{
			if (focusMode)
			{
				SetFocusMode(on: false);
			}
			selectedQuietFrame = ((quietFrames.Count > 0) ? quietFrames[rnd.Next(quietFrames.Count)] : null);
			if (state == MascotState.Idle || state == MascotState.Walking)
			{
				EnterState(MascotState.Idle);
			}
			ShowSpeech(RandomLine(QuietLines), 15000);
		}
		RedrawNow();
	}

	public void SetFocusMode(bool on)
	{
		focusMode = on;
		if (on)
		{
			if (quietMode)
			{
				SetQuietMode(on: false);
			}
			focusStartTime = DateTime.Now;
			focusTier = -1;
			ScheduleFocusChatter();
			if (state == MascotState.Idle || state == MascotState.Walking)
			{
				EnterState(MascotState.Idle);
			}
			CheckFocusMode();
		}
		else
		{
			focusTier = -1;
			selectedFocusFrame = null;
			focusHalfShown = false;
			restUntil = DateTime.MinValue;
			pendingFocusFrame = null;
			nextFocusChatter = DateTime.MaxValue;
			endingFocus = false;
			CloseFocusChoices();
		}
		RedrawNow();
	}

	private void FadeToFocusFrame(Image next)
	{
		prevFocusFrame = selectedFocusFrame;
		selectedFocusFrame = next;
		focusFadeStart = DateTime.Now;
	}

	private void CheckFocusMode()
	{
		if (!focusMode)
		{
			return;
		}
		double totalMinutes = (DateTime.Now - focusStartTime).TotalMinutes;
		if (endingFocus)
		{
			if (DateTime.Now >= restUntil)
			{
				FinishEndingFocus();
			}
			return;
		}
		if (pendingFocusFrame != null)
		{
			if (DateTime.Now < restUntil)
			{
				return;
			}
			FadeToFocusFrame(pendingFocusFrame);
			pendingFocusFrame = null;
			ShowSpeech(RandomLine(FocusWorkLines), 8000);
			RedrawNow();
		}
		int num = 0;
		for (int num2 = FocusTierMinutes.Length - 1; num2 >= 0; num2--)
		{
			if (totalMinutes >= (double)FocusTierMinutes[num2])
			{
				num = num2;
				break;
			}
		}
		bool flag = num == 5;
		int num3 = (flag ? ((int)((totalMinutes - 300.0) / 30.0)) : (-1));
		bool flag2 = num != focusTier;
		bool flag3 = flag && num3 != focusFiveHourSubTier;
		if (flag2 || flag3)
		{
			bool flag4 = focusTier < 0;
			focusTier = num;
			focusFiveHourSubTier = num3;
			focusHalfShown = false;
			if (num == 5)
			{
				bool flag5 = rnd.Next(2) == 0;
				FadeToFocusFrame(focusImages[flag5 ? 7 : 8]);
				ShowSpeech(RandomLine(FocusEncourageLines), 8000);
			}
			else if (!flag4 && (num == 1 || num == 2) && restImage != null)
			{
				FadeToFocusFrame(restImage);
				pendingFocusFrame = focusImages[num + 1];
				restUntil = DateTime.Now.AddSeconds(12.0);
				ShowSpeech(RandomLine(StretchLines), 12000);
			}
			else
			{
				FadeToFocusFrame(focusImages[num + 1]);
				ShowSpeech(RandomLine(FocusWorkLines), 8000);
			}
			RedrawNow();
		}
		else if (num == 0 && !focusHalfShown && totalMinutes >= 10.0 && focusHalfImage != null)
		{
			focusHalfShown = true;
			FadeToFocusFrame(focusHalfImage);
			ShowSpeech(RandomLine(FocusWorkLines), 8000);
			RedrawNow();
		}
		else if (DateTime.Now >= nextFocusChatter)
		{
			if (speechTicksRemaining > 0)
			{
				nextFocusChatter = DateTime.Now.AddMinutes(1.0);
				return;
			}
			ShowSpeech(RandomLine((focusTier == 5) ? FocusEncourageLines : FocusWorkLines), 8000);
			ScheduleFocusChatter();
		}
	}

	private void ToggleFocusChoices()
	{
		//IL_006d: Unknown result type (might be due to invalid IL or missing references)
		//IL_0077: Expected O, but got Unknown
		if (focusChoices != null && !((Control)focusChoices).IsDisposed)
		{
			((Form)focusChoices).Close();
			focusChoices = null;
		}
		else
		{
			if (endingFocus)
			{
				return;
			}
			focusChoices = new ChoiceBubbleForm(new string[2] { "더 집중하자!", "이제 그만 쉬자" }, delegate(int pick)
			{
				focusChoices = null;
				if (focusMode)
				{
					if (pick == 0)
					{
						ShowSpeech(RandomLine(KeepFocusLines), 4000);
					}
					else
					{
						EndFocusWithStretch();
					}
				}
			});
			((Form)focusChoices).FormClosed += (FormClosedEventHandler)delegate
			{
				if (focusChoices != null && ((Control)focusChoices).IsDisposed)
				{
					focusChoices = null;
				}
			};
			focusChoices.ShowNear(((Control)this).Bounds);
		}
	}

	private void CloseFocusChoices()
	{
		if (focusChoices != null && !((Control)focusChoices).IsDisposed)
		{
			((Form)focusChoices).Close();
		}
		focusChoices = null;
	}

	private void EndFocusWithStretch()
	{
		endingFocus = true;
		pendingFocusFrame = null;
		if (restImage != null)
		{
			FadeToFocusFrame(restImage);
		}
		restUntil = DateTime.Now.AddSeconds(5.0);
		ShowSpeech(RandomLine(StretchLines), 5000);
		RedrawNow();
	}

	private void FinishEndingFocus()
	{
		endingFocus = false;
		SetFocusMode(on: false);
		if (this.FocusModeChanged != null)
		{
			this.FocusModeChanged(obj: false);
		}
		EnterState(MascotState.Walking);
		ShowSpeech(RandomLine(FocusDoneLines), 5000);
		RedrawNow();
	}

	private void ScheduleFocusChatter()
	{
		nextFocusChatter = DateTime.Now.AddMinutes(20.0 + rnd.NextDouble() * 20.0);
	}

	public void ShowAlert(string message, string type)
	{
		//IL_0183: Unknown result type (might be due to invalid IL or missing references)
		//IL_018d: Expected O, but got Unknown
		if (ropeLine != null)
		{
			((Control)ropeLine).Hide();
		}
		isDriving = false;
		alertMessage = message;
		alertTicksRemaining = Ticks(5000);
		selectedAlertFrame = null;
		if (type == "식사시간" && idleFrames.Count >= 6)
		{
			selectedAlertFrame = idleFrames[5];
			speechText = RandomLine(MealLines);
		}
		else if (type == "퇴근시간" && idleFrames.Count >= 7)
		{
			selectedAlertFrame = idleFrames[6];
			speechText = RandomLine(LeaveLines);
		}
		else
		{
			if (alertFrames.Count > 0)
			{
				selectedAlertFrame = alertFrames[rnd.Next(alertFrames.Count)];
			}
			speechText = message;
		}
		speechTicksRemaining = alertTicksRemaining;
		speechCooldownTicks = alertTicksRemaining + Ticks(4000);
		state = MascotState.Alerting;
		frameIndex = 0;
		if (alertDialog != null)
		{
			((Form)alertDialog).Close();
			alertDialog = null;
		}
		AlarmDialogForm dlg = new AlarmDialogForm("병아리대원 알림", message);
		dlg.OnConfirm = delegate
		{
			alertDialog = null;
			DismissAlertNow();
		};
		((Form)dlg).FormClosed += (FormClosedEventHandler)delegate
		{
			if (alertDialog == dlg)
			{
				alertDialog = null;
			}
		};
		alertDialog = dlg;
		((Control)dlg).Show();
		if (edgeGlow == null)
		{
			edgeGlow = new EdgeGlowForm();
		}
		edgeGlow.SetTheme(AppSettings.GlowTheme);
		edgeGlow.ShowGlow(((Control)dlg).Bounds);
		((Control)dlg).Move += delegate
		{
			if (edgeGlow != null)
			{
				edgeGlow.FollowTarget(((Control)dlg).Bounds);
			}
		};
		((Control)dlg).BringToFront();
		((Form)dlg).Activate();
		RedrawNow();
	}

	/// <summary>업무보조 달력이 보낸 질문: 병아리가 알림 자세로 말하고, 옆에 선택 버튼 말풍선을 띄운다.</summary>
	public void AskCalendar(string message, string[] options, Action<int> onPick, Action onNoPick)
	{
		if (ropeLine != null)
		{
			((Control)ropeLine).Hide();
		}
		isDriving = false;
		alertMessage = message;
		alertTicksRemaining = Ticks(60000);
		selectedAlertFrame = (alertFrames.Count > 0) ? alertFrames[rnd.Next(alertFrames.Count)] : null;
		speechText = message;
		speechTicksRemaining = alertTicksRemaining;
		speechCooldownTicks = alertTicksRemaining + Ticks(4000);
		state = MascotState.Alerting;
		frameIndex = 0;
		bool picked = false;
		ChoiceBubbleForm bubble = new ChoiceBubbleForm(options, delegate(int pick)
		{
			picked = true;
			DismissAlertNow();
			onPick(pick);
		}, 60000);
		((Form)bubble).FormClosed += (FormClosedEventHandler)delegate
		{
			if (!picked)
			{
				DismissAlertNow();
				onNoPick();
			}
		};
		bubble.ShowNear(((Control)this).Bounds);
		if (edgeGlow == null)
		{
			edgeGlow = new EdgeGlowForm();
		}
		edgeGlow.SetTheme(AppSettings.GlowTheme);
		edgeGlow.ShowGlow(((Control)bubble).Bounds);
		RedrawNow();
	}

	/// <summary>질문에 답한 뒤 병아리가 한마디 한다.</summary>
	public void SayCalendar(string text)
	{
		ShowSpeech(text, 4000);
	}

	private TalkBoxForm talkBox;

	private Timer hopTimer;

	private int hopsLeft;

	/// <summary>말풍선을 보여 주는 중이거나 달력 질문 중인가 (그동안은 달력 말을 미룬다)</summary>
	public bool SpeechBusy => speechTicksRemaining > 0 || state == MascotState.Alerting || talkBox != null;

	/// <summary>병아리를 한 번 누르면: 달력과 연결돼 있으면 '무슨 할 말 있어요?' 창</summary>
	private void OpenTalkBox()
	{
		if (!CalendarBridge.Linked)
		{
			ShowSpeech("삐약? 업무보조 달력에서 [병아리대원 출동]을 누르면 메모도 받아 적을 수 있어요!", 5000);
			RedrawNow();
			return;
		}
		if (talkBox != null)
		{
			talkBox.Activate();
			return;
		}
		ShowSpeech("삐약! 무슨 할 말 있어요?", 3000);
		RedrawNow();
		talkBox = new TalkBoxForm(delegate(string text)
		{
			CalendarBridge.SendMemo("memo", text);
			ShowSpeech(CalendarBridge.CalendarRunning ? "받아 적는 중이에요… 삐약!" : "달력이 꺼져 있어요. 달력을 켜면 바로 적을게요!", 4000);
			RedrawNow();
		}, delegate
		{
			CalendarBridge.SendMemo("today", "");
			ShowSpeech(CalendarBridge.CalendarRunning ? "잠깐만요, 달력 보고 올게요!" : "달력이 꺼져 있어서 볼 수가 없어요 ㅠㅠ", 4000);
			RedrawNow();
		});
		((Form)talkBox).FormClosed += (FormClosedEventHandler)delegate
		{
			talkBox = null;
		};
		talkBox.ShowNear(((Control)this).Bounds);
	}

	/// <summary>달력이 시킨 반응. kind: say / brief / dance(축하 춤) / cheer(응원) / worry(걱정)</summary>
	public void CalendarReact(string kind, string text)
	{
		int ms = (kind == "brief") ? 15000 : ((kind == "worry") ? 9000 : 6000);
		bool canMove = !quietMode && !focusMode && !dragging && !isDriving
			&& (state == MascotState.Walking || state == MascotState.Idle);
		if (kind == "worry" && canMove)
		{
			EnterState(MascotState.Idle);               // 걷다가 멈춰서 걱정
			velX = 0;
			stateTicksRemaining = Ticks(ms);
			if (alertFrames.Count > 0)
			{
				selectedIdleFrame = alertFrames[rnd.Next(alertFrames.Count)];
				selectedIdlePoseIndex = -1;
			}
		}
		ShowSpeech(text, ms);
		if (canMove && (kind == "dance" || kind == "cheer" || kind == "brief"))
		{
			Hop(kind == "dance" ? 5 : 1);
		}
		RedrawNow();
	}

	/// <summary>제자리에서 콩콩 뛰기 (축하 춤)</summary>
	private void Hop(int times)
	{
		hopsLeft = times;
		if (hopTimer == null)
		{
			hopTimer = new Timer();
			hopTimer.Interval = 650;
			hopTimer.Tick += delegate
			{
				if (hopsLeft <= 0 || dragging || focusMode || isDriving)
				{
					hopTimer.Stop();
					return;
				}
				if (state != MascotState.Walking && state != MascotState.Idle)
				{
					return;                             // 아직 공중이면 내려올 때까지
				}
				hopsLeft--;
				isThrown = false;
				EnterState(MascotState.Airborne);
				velX = (hopsLeft % 2 == 0) ? 2 : -2;    // 좌우로 번갈아 콩콩
				velY = -13;
			};
		}
		hopTimer.Stop();
		hopTimer.Start();
	}

	private void DismissAlertNow()
	{
		if (edgeGlow != null)
		{
			edgeGlow.HideGlow();
		}
		if (state == MascotState.Alerting)
		{
			alertTicksRemaining = 0;
			speechTicksRemaining = 0;
			EnterState(MascotState.Idle);
			RedrawNow();
		}
	}

	private string RandomLine(string[] bank)
	{
		return bank[rnd.Next(bank.Length)];
	}

	private string[] GeneralBankForNow()
	{
		int hour = DateTime.Now.Hour;
		if (hour >= 5 && hour < 10)
		{
			return MorningLines;
		}
		if (hour >= 17 && hour < 21)
		{
			return LeaveLines;
		}
		return PositiveLines;
	}

	private void ShowSpeech(string text, int durationMs)
	{
		speechText = text;
		speechTicksRemaining = Ticks(durationMs);
		speechCooldownTicks = Ticks(durationMs + 4000);
	}

	public void TriggerContextualSpeech()
	{
		string[] array = (focusMode ? ((pendingFocusFrame != null) ? StretchLines : ((focusTier == 5) ? FocusEncourageLines : FocusWorkLines)) : (quietMode ? QuietLines : (deepSleepActive ? SleepLines : ((welcomeBackTicksRemaining > 0) ? SaluteLines : (longIdleActive ? IdlePoseLines[2] : (giftActive ? GiftLines : ((state == MascotState.Walking) ? (isDriving ? DriveLines : (dashActive ? RunLines : WalkLines)) : ((state == MascotState.Airborne) ? (isThrown ? ThrownLines : FallLines) : ((state == MascotState.RopeDescending) ? RopeDownLines : ((state == MascotState.Climbing) ? ClimbLines : ((state == MascotState.RopeClimbing) ? RopeUpLines : ((state == MascotState.Alerting) ? null : ((selectedIdlePoseIndex < 0 || selectedIdlePoseIndex >= IdlePoseLines.Length) ? GeneralBankForNow() : IdlePoseLines[selectedIdlePoseIndex])))))))))))));
		if (array != null && array.Length > 0)
		{
			ShowSpeech(RandomLine(array), 3500);
		}
	}

	private List<Image> CurrentFrameSet()
	{
		switch (state)
		{
		case MascotState.Alerting:
			if (selectedAlertFrame != null)
			{
				List<Image> list6 = new List<Image>();
				list6.Add(selectedAlertFrame);
				return list6;
			}
			if (alertFrames.Count <= 0)
			{
				return idleFrames;
			}
			return alertFrames;
		case MascotState.Walking:
			if (isDriving && selectedCarFrame != null)
			{
				List<Image> list7 = new List<Image>();
				list7.Add(selectedCarFrame);
				return list7;
			}
			if (dashActive && runFrame != null)
			{
				List<Image> list8 = new List<Image>();
				list8.Add(runFrame);
				return list8;
			}
			if (walkFrames.Count <= 0)
			{
				return idleFrames;
			}
			return walkFrames;
		case MascotState.Airborne:
			if (isThrown)
			{
				if (flyFrames.Count <= 0)
				{
					if (fallFrames.Count <= 0)
					{
						if (walkFrames.Count <= 0)
						{
							return idleFrames;
						}
						return walkFrames;
					}
					return fallFrames;
				}
				return flyFrames;
			}
			if (fallFrames.Count <= 0)
			{
				if (flyFrames.Count <= 0)
				{
					if (walkFrames.Count <= 0)
					{
						return idleFrames;
					}
					return walkFrames;
				}
				return flyFrames;
			}
			return fallFrames;
		case MascotState.Climbing:
			if (climbFrames.Count <= 0)
			{
				return idleFrames;
			}
			return climbFrames;
		case MascotState.RopeClimbing:
			if (ropeUpPhase == 1 && climbFrames.Count > 0)
			{
				List<Image> list5 = new List<Image>();
				list5.Add(climbFrames[0]);
				return list5;
			}
			if (upFrames.Count <= 0)
			{
				return idleFrames;
			}
			return upFrames;
		case MascotState.RopeDescending:
			if (descendPhase == 0)
			{
				if (flyFrames.Count <= 0)
				{
					if (fallFrames.Count <= 0)
					{
						return idleFrames;
					}
					return fallFrames;
				}
				return flyFrames;
			}
			if (fallFrames.Count <= 0)
			{
				if (flyFrames.Count <= 0)
				{
					return idleFrames;
				}
				return flyFrames;
			}
			return fallFrames;
		default:
			if (giftActive && selectedGiftFrame != null)
			{
				List<Image> list = new List<Image>();
				list.Add(selectedGiftFrame);
				return list;
			}
			if (focusMode && selectedFocusFrame != null)
			{
				List<Image> list2 = new List<Image>();
				list2.Add(selectedFocusFrame);
				return list2;
			}
			if (quietMode && selectedQuietFrame != null)
			{
				List<Image> list3 = new List<Image>();
				list3.Add(selectedQuietFrame);
				return list3;
			}
			if (deepSleepActive && sleepFrames.Count > 0)
			{
				return sleepFrames;
			}
			if (longIdleActive && longIdleFrames.Count > 0)
			{
				return longIdleFrames;
			}
			if (welcomeBackTicksRemaining > 0 && welcomeBackFrames.Count > 0)
			{
				return welcomeBackFrames;
			}
			if (selectedIdleFrame != null)
			{
				List<Image> list4 = new List<Image>();
				list4.Add(selectedIdleFrame);
				return list4;
			}
			return idleFrames;
		}
	}

	private void RedrawNow()
	{
		//IL_005e: Unknown result type (might be due to invalid IL or missing references)
		//IL_0068: Expected O, but got Unknown
		lastRedrawTick = Environment.TickCount;
		if (frameBuffer == null || ((Image)frameBuffer).Width != ((Control)this).Width || ((Image)frameBuffer).Height != ((Control)this).Height)
		{
			if (frameBuffer != null)
			{
				((Image)frameBuffer).Dispose();
			}
			frameBuffer = new Bitmap(((Control)this).Width, ((Control)this).Height, (PixelFormat)2498570);
		}
		Graphics val = Graphics.FromImage((Image)(object)frameBuffer);
		try
		{
			val.Clear(Color.Transparent);
			DrawFrame(val);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
		SetBitmap(frameBuffer);
		UpdateSpeechBubble();
	}

	private void UpdateSpeechBubble()
	{
		bool flag = speechTicksRemaining > 0 && !string.IsNullOrEmpty(speechText);
		string text = null;
		if (focusMode)
		{
			TimeSpan timeSpan = DateTime.Now - focusStartTime;
			string text2 = $"집중 {(int)timeSpan.TotalHours:00}:{timeSpan.Minutes:00}:{timeSpan.Seconds:00}";
			text = (flag ? (text2 + "\n" + speechText) : text2);
		}
		else if (flag)
		{
			text = speechText;
		}
		if (!((Control)this).Visible)
		{
			text = null;
		}
		if (text != null)
		{
			if (speechBubble == null)
			{
				speechBubble = new SpeechBubbleForm();
			}
			speechBubble.ShowAt(text, ((Form)this).Location.X + 95, ((Form)this).Location.Y + 40);
			bool flag2 = !((Control)speechBubble).Visible;
			if (flag2)
			{
				((Control)speechBubble).Show();
			}
			if (flag2 || Environment.TickCount - lastBubbleFrontTick > 500)
			{
				((Control)speechBubble).BringToFront();
				lastBubbleFrontTick = Environment.TickCount;
			}
		}
		else if (speechBubble != null && ((Control)speechBubble).Visible)
		{
			((Control)speechBubble).Hide();
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
			SIZEAPI psize = new SIZEAPI(((Image)bitmap).Width, ((Image)bitmap).Height);
			POINTAPI pptSrc = new POINTAPI(0, 0);
			POINTAPI pptDst = new POINTAPI(((Control)this).Left, ((Control)this).Top);
			BLENDFUNCTION pblend = new BLENDFUNCTION
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

	private void DrawFrame(Graphics g)
	{
		//IL_02e6: Unknown result type (might be due to invalid IL or missing references)
		//IL_02ed: Expected O, but got Unknown
		//IL_0302: Unknown result type (might be due to invalid IL or missing references)
		//IL_0309: Expected O, but got Unknown
		//IL_0320: Unknown result type (might be due to invalid IL or missing references)
		//IL_0327: Expected O, but got Unknown
		//IL_036d: Unknown result type (might be due to invalid IL or missing references)
		//IL_0374: Expected O, but got Unknown
		g.SmoothingMode = (SmoothingMode)4;
		bool flag = state == MascotState.Alerting;
		List<Image> list = CurrentFrameSet();
		Image val = ((list.Count > 0) ? list[frameIndex % list.Count] : null);
		if (state == MascotState.Walking && !isDriving && !dragging && list == walkFrames && list.Count >= 2)
		{
			val = list[(int)(walkBobPhase / Math.PI) % list.Count];
		}
		Rectangle rectangle = new Rectangle(10, 38, 100, 100);
		if (val != null)
		{
			GraphicsState val2 = g.Save();
			if (state == MascotState.Walking)
			{
				bool flag2 = ((velX != 0) ? (velX > 0) : (direction > 0));
				bool flag3 = !isDriving || selectedCarFacesRight;
				if (flag2 != flag3)
				{
					g.TranslateTransform((float)((Control)this).Width, 0f);
					g.ScaleTransform(-1f, 1f);
				}
			}
			if ((state == MascotState.Climbing || (state == MascotState.RopeClimbing && ropeUpPhase == 1)) && climbOnLeft)
			{
				g.TranslateTransform((float)((Control)this).Width, 0f);
				g.ScaleTransform(-1f, 1f);
			}
			int num = ((Control)this).Width - 20;
			int height = rectangle.Height;
			float num2 = (float)val.Width / (float)val.Height;
			int num3 = num;
			int num4 = (int)((float)num / num2);
			if (num4 > height)
			{
				num4 = height;
				num3 = (int)((float)height * num2);
			}
			int num5 = 10 + (num - num3) / 2;
			int num6 = rectangle.Bottom - num4;
			Rectangle rectangle2 = new Rectangle(num5, num6, num3, num4);
			g.InterpolationMode = (InterpolationMode)6;
			g.PixelOffsetMode = (PixelOffsetMode)2;
			ApplyMotion(g, val, rectangle2);
			double num7 = (DateTime.Now - focusFadeStart).TotalSeconds / 2.0;
			if (focusMode && val == selectedFocusFrame && prevFocusFrame != null && prevFocusFrame != val && num7 < 1.0)
			{
				float num8 = (float)(num7 * num7 * (3.0 - 2.0 * num7));
				DrawWithAlpha(g, prevFocusFrame, rectangle2, Math.Min(1f, 2f - 2f * num8));
				DrawWithAlpha(g, val, rectangle2, Math.Min(1f, 2f * num8));
			}
			else
			{
				g.DrawImage(val, rectangle2);
			}
			DrawEffects(g, val, rectangle2);
			g.Restore(val2);
			if (val != null && sleepFrames.Contains(val))
			{
				DrawZzz(g, rectangle2);
			}
			return;
		}
		SolidBrush val3 = new SolidBrush(Color.FromArgb(255, 245, 200, 220));
		try
		{
			Pen val4 = new Pen(Color.FromArgb(255, 120, 80, 100), 3f);
			try
			{
				g.FillEllipse((Brush)(object)val3, rectangle);
				g.DrawEllipse(val4, rectangle);
				SolidBrush val5 = new SolidBrush(Color.Black);
				try
				{
					g.FillEllipse((Brush)(object)val5, 40, 45, 10, 10);
					g.FillEllipse((Brush)(object)val5, 75, 45, 10, 10);
				}
				finally
				{
					((IDisposable)val5)?.Dispose();
				}
				Pen val6 = new Pen(Color.FromArgb(255, 150, 60, 80), 3f);
				try
				{
					if (flag)
					{
						g.DrawArc(val6, 45, 55, 30, 20, 0, 180);
					}
					else
					{
						g.DrawArc(val6, 45, 60, 30, 15, 10, 160);
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

	private void ApplyMotion(Graphics g, Image img, Rectangle r)
	{
		double clock = Clock;
		float num = 1f;
		float num2 = 1f;
		float num3 = 0f;
		float num4 = 0f;
		float num5 = (float)r.X + (float)r.Width / 2f;
		float num6 = r.Bottom;
		if (dragging)
		{
			double num7 = (((DateTime.Now - lastDragTime).TotalMilliseconds < 120.0) ? Math.Max(-14.0, Math.Min(14.0, dragVelX * 0.015)) : 0.0);
			dragTilt += (num7 - dragTilt) * 0.25;
			num3 = (float)(dragTilt + Math.Sin(clock * 5.0) * 1.5);
			num6 = r.Y + 8;
		}
		else
		{
			dragTilt = 0.0;
			switch (state)
			{
			case MascotState.Walking:
			{
				if (isDriving)
				{
					num4 = (float)(Math.Sin(clock * 37.0) * 0.8);
					num3 = (float)(Math.Sin(clock * 3.0) * 0.6);
					break;
				}
				double num17 = 1.0 - Math.Abs(Math.Sin(walkBobPhase));
				num3 = (float)(Math.Sin(walkBobPhase) * 3.5);
				num2 = (float)(1.0 - 0.035 * num17);
				num = (float)(1.0 + 0.025 * num17);
				if (dashActive)
				{
					num3 = (float)(6.0 + Math.Sin(walkBobPhase) * 2.0);
				}
				break;
			}
			case MascotState.Airborne:
				if (isThrown)
				{
					num3 = (float)(Math.Sin(clock * 2.2) * 4.0);
					num4 = (float)(Math.Sin(clock * 3.1) * 2.5);
				}
				else
				{
					num3 = (float)(Math.Sin(clock * 14.0) * 5.0);
				}
				break;
			case MascotState.Alerting:
			{
				double num16 = Math.Abs(Math.Sin(clock * 6.0));
				num4 = (float)((0.0 - num16) * 5.0);
				num2 = (float)(1.0 + 0.04 * num16);
				num = (float)(1.0 - 0.03 * num16);
				break;
			}
			default:
			{
				if (giftActive)
				{
					num3 = (float)(Math.Sin(clock * 1.8) * 2.5);
					num4 = (float)((0.0 - Math.Abs(Math.Sin(clock * 2.4))) * 1.5);
					break;
				}
				if (focusMode && img == restImage && restImage != null)
				{
					double num8 = (1.0 - Math.Cos(clock * 2.0 * Math.PI / 2.4)) / 2.0;
					num2 = (float)(1.0 + 0.045 * num8);
					num = (float)(1.0 - 0.015 * num8);
					num3 = (float)(Math.Sin(clock * 2.0 * Math.PI / 4.8) * 2.5);
					break;
				}
				if (focusMode)
				{
					double num9 = (DateTime.Now - focusStartTime).TotalSeconds % 60.0;
					if (num9 > 58.5)
					{
						double num10 = Math.Sin((num9 - 58.5) / 1.5 * Math.PI);
						num2 = (float)(1.0 + 0.03 * num10);
						num = (float)(1.0 - 0.01 * num10);
					}
					break;
				}
				bool flag = sleepFrames.Contains(img);
				double num11 = Math.Sin(clock * 2.0 * Math.PI / (flag ? 4.5 : 3.0));
				double num12 = (flag ? 0.035 : 0.022);
				num2 = (float)(1.0 + num12 * num11);
				num = (float)(1.0 - num12 * 0.5 * num11);
				double totalSeconds = (DateTime.Now - poseStartTime).TotalSeconds;
				switch (ExtraPoseIndex(img))
				{
				case 2:
					num4 = (float)((0.0 - Math.Abs(Math.Sin(clock * 4.0))) * 2.5);
					num3 = (float)(Math.Sin(clock * 2.0) * 2.0);
					break;
				case 3:
					num3 = (float)(Math.Sin(clock * 1.6) * 2.5);
					break;
				case 4:
				{
					double num15 = Math.Max(0.0, Math.Sin(clock * 2.4));
					num2 *= (float)(1.0 - 0.05 * num15);
					num4 += (float)(num15 * 1.5);
					break;
				}
				case 5:
					num4 = (float)((0.0 - Math.Abs(Math.Sin(clock * 2.5))) * 1.5);
					break;
				case 7:
				{
					double num13 = clock % 1.2 / 1.2;
					double num14 = Math.Max(0.0, Math.Sin(num13 * Math.PI * 6.0)) * (double)((num13 < 0.34) ? 1 : 0);
					num *= (float)(1.0 + 0.03 * num14);
					num2 *= (float)(1.0 + 0.03 * num14);
					break;
				}
				case 8:
					if (totalSeconds < 0.45)
					{
						num4 = (float)((0.0 - Math.Sin(totalSeconds / 0.45 * Math.PI)) * 8.0);
					}
					break;
				case 9:
					num4 = (float)((0.0 - Math.Abs(Math.Sin(clock * 5.0))) * 1.5);
					break;
				}
				break;
			}
			case MascotState.RopeDescending:
			case MascotState.Climbing:
			case MascotState.RopeClimbing:
				break;
			}
			if (landImpact > 0.0)
			{
				num2 *= (float)(1.0 - 0.14 * landImpact);
				num *= (float)(1.0 + 0.1 * landImpact);
			}
		}
		g.TranslateTransform(num5, num6 + num4);
		if (num3 != 0f)
		{
			g.RotateTransform(num3);
		}
		g.ScaleTransform(num, num2);
		g.TranslateTransform(0f - num5, 0f - num6);
	}

	private void DrawEffects(Graphics g, Image img, Rectangle r)
	{
		//IL_02d3: Unknown result type (might be due to invalid IL or missing references)
		//IL_02da: Expected O, but got Unknown
		//IL_05ac: Unknown result type (might be due to invalid IL or missing references)
		//IL_05b3: Expected O, but got Unknown
		//IL_06f3: Unknown result type (might be due to invalid IL or missing references)
		//IL_06fa: Expected O, but got Unknown
		double clock = Clock;
		Func<float, float, PointF> func = (float fx, float fy) => new PointF((float)r.X + fx * (float)r.Width, (float)r.Y + fy * (float)r.Height);
		float num = (float)r.Width / 100f;
		if (giftActive && giftFrames.Contains(img))
		{
			DrawGiftHearts(g, r, clock, DateTime.Now < heartBurstUntil);
			return;
		}
		switch (ExtraPoseIndex(img))
		{
		case 3:
		case 7:
		{
			for (int num2 = 0; num2 < 2; num2++)
			{
				double num3 = (clock * 0.28 + (double)num2 * 0.5) % 1.0;
				float cx = (float)r.X + (float)r.Width * ((num2 == 0) ? 0.12f : 0.88f) + (float)(Math.Sin(num3 * 5.0 + (double)num2) * 3.0) * num;
				float cy = (float)r.Y + (float)r.Height * 0.55f - (float)(num3 * 0.55) * (float)r.Height;
				FillHeart(g, cx, cy, (float)(4.0 + 2.0 * Math.Sin(num3 * Math.PI)) * num, (int)(Math.Sin(num3 * Math.PI) * 200.0));
			}
			return;
		}
		case 5:
			DrawTwinkle(g, func(0.9f, 0.33f), num, clock);
			return;
		case 9:
			DrawTwinkle(g, func(0.88f, 0.15f), num, clock);
			return;
		}
		if (state == MascotState.Walking && dashActive && !isDriving)
		{
			for (int num4 = 0; num4 < 3; num4++)
			{
				double num5 = (clock * 2.2 + (double)num4 / 3.0) % 1.0;
				float num6 = (float)(1.5 + num5 * 4.0) * num;
				float num7 = (float)r.X + (float)r.Width * 0.25f - (float)(num5 * 14.0) * num;
				float num8 = (float)r.Bottom - 3f * num - (float)(num5 * 5.0) * num;
				SolidBrush val = new SolidBrush(Color.FromArgb((int)((1.0 - num5) * 110.0), 190, 180, 165));
				try
				{
					g.FillEllipse((Brush)(object)val, num7 - num6, num8 - num6, num6 * 2f, num6 * 2f);
				}
				finally
				{
					((IDisposable)val)?.Dispose();
				}
			}
			return;
		}
		if (img != null && img == focusHalfImage)
		{
			DrawSteam(g, func(0.13f, 0.58f), num, clock, 12f, -1f);
			return;
		}
		if (img != null && img == restImage)
		{
			DrawSteam(g, func(0.255f, 0.6f), num, clock, 12f, -1f);
			return;
		}
		int num9 = Array.IndexOf(focusImages, img);
		if (num9 > 0)
		{
			if (num9 < FocusSteamAt.Length && FocusSteamAt[num9] != PointF.Empty)
			{
				DrawSteam(g, func(FocusSteamAt[num9].X, FocusSteamAt[num9].Y), num, clock, FocusSteamRise[num9], (num9 <= 3) ? (-1) : 0);
			}
			if (num9 == 4)
			{
				DrawEyeFire(g, func(0.46f, 0.46f), num * 0.8f, clock, 0.0);
				DrawEyeFire(g, func(0.61f, 0.46f), num * 0.8f, clock, 1.7);
			}
			if (num9 == 5)
			{
				DrawEyeFire(g, func(0.49f, 0.46f), num, clock, 0.0);
				DrawEyeFire(g, func(0.67f, 0.46f), num, clock, 1.7);
			}
			if (num9 == 8)
			{
				DrawTear(g, func(0.43f, 0.5f), num, clock, 0.0);
				DrawTear(g, func(0.66f, 0.5f), num, clock, 0.5);
			}
			return;
		}
		if (state == MascotState.Airborne && isThrown && flyFrames.Contains(img))
		{
			for (int num10 = 0; num10 < 2; num10++)
			{
				PointF pointF = func((num10 == 0) ? 0.18f : 0.85f, 0.075f);
				int alpha = (int)(70.0 + 50.0 * Math.Abs(Math.Sin(clock * 47.0 + (double)num10 * 1.3)));
				float num11 = 16f * num * (float)(0.85 + 0.15 * Math.Sin(clock * 31.0 + (double)num10));
				SolidBrush val2 = new SolidBrush(Color.FromArgb(alpha, 200, 215, 230));
				try
				{
					g.FillEllipse((Brush)(object)val2, pointF.X - num11 / 2f, pointF.Y - 1.6f * num, num11, 3.2f * num);
				}
				finally
				{
					((IDisposable)val2)?.Dispose();
				}
			}
			return;
		}
		if (state != MascotState.Walking || !isDriving)
		{
			return;
		}
		float num12 = ((!selectedCarFacesRight) ? 1 : (-1));
		PointF pointF2 = func(selectedCarFacesRight ? 0.03f : 0.97f, 0.86f);
		for (int num13 = 0; num13 < 3; num13++)
		{
			double num14 = (clock * 1.2 + (double)num13 / 3.0) % 1.0;
			float num15 = (float)(2.0 + num14 * 5.0) * num;
			int alpha2 = (int)((1.0 - num14) * 120.0);
			float num16 = pointF2.X + num12 * (float)(num14 * 18.0) * num;
			float num17 = pointF2.Y - (float)(num14 * 6.0) * num;
			SolidBrush val3 = new SolidBrush(Color.FromArgb(alpha2, 170, 170, 175));
			try
			{
				g.FillEllipse((Brush)(object)val3, num16 - num15, num17 - num15, num15 * 2f, num15 * 2f);
			}
			finally
			{
				((IDisposable)val3)?.Dispose();
			}
		}
	}

	private static void DrawWithAlpha(Graphics g, Image img, Rectangle r, float alpha)
	{
		//IL_0009: Unknown result type (might be due to invalid IL or missing references)
		//IL_000f: Expected O, but got Unknown
		//IL_0022: Unknown result type (might be due to invalid IL or missing references)
		//IL_0028: Expected O, but got Unknown
		if (alpha <= 0.01f)
		{
			return;
		}
		ColorMatrix val = new ColorMatrix();
		val.Matrix33 = Math.Min(1f, alpha);
		ColorMatrix colorMatrix = val;
		ImageAttributes val2 = new ImageAttributes();
		try
		{
			val2.SetColorMatrix(colorMatrix);
			g.DrawImage(img, r, 0, 0, img.Width, img.Height, (GraphicsUnit)2, val2);
		}
		finally
		{
			((IDisposable)val2)?.Dispose();
		}
	}

	private int ExtraPoseIndex(Image img)
	{
		if (img == null || state != MascotState.Idle)
		{
			return 0;
		}
		int num = idleFrames.IndexOf(img);
		if (num < 7)
		{
			return 0;
		}
		return num - 6;
	}

	private static void DrawTwinkle(Graphics g, PointF c, float unit, double t)
	{
		//IL_0067: Unknown result type (might be due to invalid IL or missing references)
		//IL_006d: Expected O, but got Unknown
		//IL_006d: Unknown result type (might be due to invalid IL or missing references)
		//IL_0074: Expected O, but got Unknown
		double num = Math.Max(0.0, Math.Sin(t * 3.2));
		if (num <= 0.05)
		{
			return;
		}
		float num2 = (float)(2.0 + 4.0 * num) * unit;
		int alpha = (int)(num * 230.0);
		SolidBrush val = new SolidBrush(Color.FromArgb(alpha, 255, 255, 235));
		try
		{
			GraphicsPath val2 = new GraphicsPath();
			try
			{
				val2.AddPolygon(new PointF[8]
				{
					new PointF(c.X, c.Y - num2),
					new PointF(c.X + num2 * 0.22f, c.Y - num2 * 0.22f),
					new PointF(c.X + num2, c.Y),
					new PointF(c.X + num2 * 0.22f, c.Y + num2 * 0.22f),
					new PointF(c.X, c.Y + num2),
					new PointF(c.X - num2 * 0.22f, c.Y + num2 * 0.22f),
					new PointF(c.X - num2, c.Y),
					new PointF(c.X - num2 * 0.22f, c.Y - num2 * 0.22f)
				});
				g.FillPath((Brush)(object)val, val2);
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

	private static void DrawGiftHearts(Graphics g, Rectangle r, double t, bool burst)
	{
		float num = (float)r.Width / 100f;
		for (int i = 0; i < 4; i++)
		{
			double num2 = (t * 0.3 + (double)i / 4.0) % 1.0;
			bool flag = i % 2 == 0;
			float cx = (float)r.X + (float)r.Width * (flag ? 0.16f : 0.84f) + (float)(Math.Sin(num2 * 5.0 + (double)i) * 4.0) * num;
			float cy = (float)r.Y + (float)r.Height * 0.6f - (float)(num2 * 0.7) * (float)r.Height;
			float s = (float)(5.0 + 3.0 * Math.Sin(num2 * Math.PI)) * num;
			int alpha = (int)(Math.Sin(num2 * Math.PI) * 220.0);
			FillHeart(g, cx, cy, s, alpha);
		}
		if (burst)
		{
			for (int j = 0; j < 7; j++)
			{
				double num3 = (t * 0.9 + (double)j / 7.0) % 1.0;
				double num4 = -Math.PI / 2.0 + (double)(j - 3) * 0.38;
				float num5 = (float)(num3 * 0.55) * (float)r.Height;
				float cx2 = (float)r.X + (float)r.Width * 0.5f + (float)Math.Cos(num4) * num5;
				float cy2 = (float)r.Y + (float)r.Height * 0.55f + (float)Math.Sin(num4) * num5;
				FillHeart(g, cx2, cy2, (float)(4.0 + 4.0 * num3) * num, (int)((1.0 - num3) * 240.0));
			}
		}
	}

	private static void FillHeart(Graphics g, float cx, float cy, float s, int alpha)
	{
		//IL_0006: Unknown result type (might be due to invalid IL or missing references)
		//IL_000c: Expected O, but got Unknown
		//IL_00a1: Unknown result type (might be due to invalid IL or missing references)
		//IL_00a7: Expected O, but got Unknown
		//IL_00d5: Unknown result type (might be due to invalid IL or missing references)
		//IL_00db: Expected O, but got Unknown
		if (alpha <= 0)
		{
			return;
		}
		GraphicsPath val = new GraphicsPath();
		try
		{
			val.AddBezier(cx, cy + s * 0.55f, cx - s * 1.1f, cy - s * 0.1f, cx - s * 0.55f, cy - s * 0.9f, cx, cy - s * 0.35f);
			val.AddBezier(cx, cy - s * 0.35f, cx + s * 0.55f, cy - s * 0.9f, cx + s * 1.1f, cy - s * 0.1f, cx, cy + s * 0.55f);
			val.CloseFigure();
			SolidBrush val2 = new SolidBrush(Color.FromArgb(alpha, 255, 110, 140));
			try
			{
				g.FillPath((Brush)(object)val2, val);
			}
			finally
			{
				((IDisposable)val2)?.Dispose();
			}
			SolidBrush val3 = new SolidBrush(Color.FromArgb(alpha * 2 / 3, 255, 215, 225));
			try
			{
				g.FillEllipse((Brush)(object)val3, cx - s * 0.45f, cy - s * 0.55f, s * 0.28f, s * 0.22f);
			}
			finally
			{
				((IDisposable)val3)?.Dispose();
			}
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	private static void DrawSteam(Graphics g, PointF cup, float unit, double t, float rise, float drift)
	{
		//IL_00cb: Unknown result type (might be due to invalid IL or missing references)
		//IL_00d2: Expected O, but got Unknown
		for (int i = 0; i < 3; i++)
		{
			double num = (t * 0.45 + (double)i / 3.0) % 1.0;
			float num2 = cup.Y - (float)(num * (double)rise) * unit;
			float num3 = cup.X + (float)((double)drift * num * 7.0 + Math.Sin(num * 6.0 + (double)i * 2.1) * 2.0) * unit;
			float num4 = (float)(2.5 + num * 4.5) * unit;
			int alpha = (int)(Math.Sin(num * Math.PI) * 170.0);
			SolidBrush val = new SolidBrush(Color.FromArgb(alpha, 185, 185, 195));
			try
			{
				g.FillEllipse((Brush)(object)val, num3 - num4 / 2f, num2 - num4 / 2f, num4, num4);
			}
			finally
			{
				((IDisposable)val)?.Dispose();
			}
		}
	}

	private static void DrawEyeFire(Graphics g, PointF eye, float unit, double t, double seed)
	{
		//IL_0097: Unknown result type (might be due to invalid IL or missing references)
		//IL_009e: Expected O, but got Unknown
		//IL_00fe: Unknown result type (might be due to invalid IL or missing references)
		//IL_0105: Expected O, but got Unknown
		float num = (float)(1.0 + 0.18 * Math.Sin(t * 13.0 + seed) + 0.08 * Math.Sin(t * 29.0 + seed * 2.0));
		float num2 = (float)(Math.Sin(t * 7.0 + seed) * 0.8) * unit;
		float num3 = 7f * unit;
		float num4 = 9f * unit * num;
		SolidBrush val = new SolidBrush(Color.FromArgb(150, 255, 110, 20));
		try
		{
			g.FillEllipse((Brush)(object)val, eye.X - num3 / 2f + num2, eye.Y - num4 * 0.7f, num3, num4);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
		float num5 = num3 * 0.55f;
		float num6 = num4 * 0.6f;
		SolidBrush val2 = new SolidBrush(Color.FromArgb(190, 255, 220, 70));
		try
		{
			g.FillEllipse((Brush)(object)val2, eye.X - num5 / 2f + num2 * 0.5f, eye.Y - num6 * 0.55f, num5, num6);
		}
		finally
		{
			((IDisposable)val2)?.Dispose();
		}
	}

	private static void DrawTear(Graphics g, PointF eye, float unit, double t, double offset)
	{
		//IL_0061: Unknown result type (might be due to invalid IL or missing references)
		//IL_0068: Expected O, but got Unknown
		double num = (t * 0.8 + offset) % 1.0;
		float num2 = eye.Y + (float)(num * 14.0) * unit;
		int alpha = (int)((1.0 - num) * 210.0);
		float num3 = 3.2f * unit;
		SolidBrush val = new SolidBrush(Color.FromArgb(alpha, 110, 185, 245));
		try
		{
			g.FillEllipse((Brush)(object)val, eye.X - num3 / 2f, num2 - num3 / 2f, num3, num3 * 1.3f);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	private static void DrawZzz(Graphics g, Rectangle r)
	{
		//IL_00a8: Unknown result type (might be due to invalid IL or missing references)
		//IL_00af: Expected O, but got Unknown
		double clock = Clock;
		for (int i = 0; i < 3; i++)
		{
			double num = (clock * 0.35 + (double)i / 3.0) % 1.0;
			float num2 = (float)r.X + (float)r.Width * 0.7f + (float)(num * 24.0);
			float num3 = (float)r.Y + (float)r.Height * 0.12f - (float)(num * 30.0);
			int alpha = (int)(Math.Sin(num * Math.PI) * 230.0);
			SolidBrush val = new SolidBrush(Color.FromArgb(alpha, 90, 110, 180));
			try
			{
				g.DrawString("Z", ZFonts[(int)Math.Round(num * 6.0)], (Brush)(object)val, num2, num3);
			}
			finally
			{
				((IDisposable)val)?.Dispose();
			}
		}
	}

	protected override void OnPaintBackground(PaintEventArgs e)
	{
	}
}
