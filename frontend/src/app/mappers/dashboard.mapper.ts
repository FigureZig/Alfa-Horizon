import {DashboardStatisticsDto } from '@/app/types/dashboard/dashboard-statistics-dto.ts'
import {DashboardStatisticInterface} from "@/app/types/dashboard/dashboard-statistic-interface.ts";

export class DashboardMapper {
    static toEntity(data: DashboardStatisticsDto): DashboardStatisticInterface {
        if (!data) {
            throw new Error('Dashboard data is required')
        }

        return {
            balance: data.total_balance,
            income: data.monthly_income,
            expenses: data.monthly_expenses,
            activeCredits: data.active_loans_count,
        }
    }
}