// 판 안의 돈 (REP-1). 광석과 수리 두 갈래만 — 상점·빚·정산 화면은 출시판. 부스 판이 시작될 때 RepairDirector 가 0 으로.
public static class Economy
{
    public static float Ore { get; private set; }
    public static float Repair { get; private set; }
    public static float Total => Ore + Repair;

    public static void AddOre(int count) => Ore += count * Tuning.ORE_VALUE;
    public static void AddRepair(float value) => Repair += value;
    public static void Reset() { Ore = 0f; Repair = 0f; }
}
