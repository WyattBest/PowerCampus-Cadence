USE [Campus6]
GO

/****** Object:  StoredProcedure [custom].[CadenceSelContacts]    Script Date: 2020-10-23 12:36:18 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


-- =============================================
-- Author:		Wyatt Best
-- Create date: 2020-10-23
-- Description:	Selects three terms' worth of students and various fields to send to Mongoose Cadence.
-- =============================================
CREATE PROCEDURE [custom].[CadenceSelContacts]
AS
BEGIN
	SET NOCOUNT ON;

	DECLARE @AcademicYear NVARCHAR(4) = (
			SELECT dbo.fnGetAbtSetting('ACA_RECORDS', 'CURRENT_YT', 'CURRENT_YEAR')
			)
		,@AcademicTerm NVARCHAR(10) = (
			SELECT dbo.fnGetAbtSetting('ACA_RECORDS', 'CURRENT_YT', 'CURRENT_TERM')
			)
		,@TermId INT
		,@SPTermId INT
		,@SUTermId INT
		,@FATermId INT

	SELECT @TermId = TermId
	FROM [custom].vwOrderedTerms OT
	WHERE ACADEMIC_YEAR = @AcademicYear
		AND ACADEMIC_TERM = @AcademicTerm

	--Find Spring, Summer, and Fall terms
	SELECT @SPTermId = CASE ACADEMIC_TERM
			WHEN 'SPRING'
				THEN @TermId
			WHEN 'SUMMER'
				THEN @TermId - 1
			WHEN 'FALL'
				THEN @TermId + 1
			END
		,@SUTermId = CASE ACADEMIC_TERM
			WHEN 'SPRING'
				THEN @TermId + 1
			WHEN 'SUMMER'
				THEN @TermId
			WHEN 'FALL'
				THEN @TermId - 1
			END
		,@FATermId = CASE ACADEMIC_TERM
			WHEN 'SPRING'
				THEN @TermId - 1
			WHEN 'SUMMER'
				THEN @TermId + 1
			WHEN 'FALL'
				THEN @TermId
			END
	FROM [custom].vwOrderedTerms OT
	WHERE TermId = @TermId

	----Debug
	--SELECT @TermId [@TermId]
	--	,@SPTermId [@SPTermId]
	--	,@SUTermId [@SUTermId]
	--	,@FATermId [@FATermId]
	--Select list of students
	SELECT DISTINCT PEOPLE_CODE_ID
	INTO #Students
	FROM [custom].vwACADEMIC A
	WHERE TermId BETWEEN @TermId - 1 AND @TermId + 2
		AND ACADEMIC_FLAG = 'Y'
		AND [STATUS] IN (
			'A'
			,'G'
			)
		AND ACADEMIC_SESSION > ''

	--Add in columns
	SELECT S.PEOPLE_CODE_ID
		,dbo.fnPeopleOrgName(S.PEOPLE_CODE_ID, 'FN') [FirstName]
		,dbo.fnPeopleOrgName(S.PEOPLE_CODE_ID, 'LN') [LastName]
		,Phone.*
		,Enrollment.SHORT_DESC [Enrollment]
		,SP_Credits.CREDITS [SP_Credits]
		,SU_Credits.CREDITS [SU_Credits]
		,FA_Credits.CREDITS [FA_Credits]
	FROM #Students S
	OUTER APPLY (
		SELECT TOP 1 CASE 
				WHEN CountryId = 240 --US country code
					THEN '1' + PP.PhoneNumber
				ELSE '??'
				END AS [Mobile]
		FROM PEOPLE P
		INNER JOIN PersonPhone PP
			ON PP.PersonId = P.PersonId
				AND DoNotCallReason IS NULL
				AND PhoneType = 'MOBILE1'
		WHERE P.PEOPLE_CODE_ID = S.PEOPLE_CODE_ID
		ORDER BY CASE 
				WHEN P.PrimaryPhoneId = PP.PersonPhoneId
					THEN GETDATE()
				ELSE PP.Revision_Date + PP.Revision_Time
				END DESC
		) AS Phone
	OUTER APPLY (
		SELECT TOP 1 SHORT_DESC
		FROM [custom].vwACADEMIC A
		INNER JOIN CODE_ENROLLMENT
			ON CODE_VALUE_KEY = ENROLL_SEPARATION
		WHERE A.PEOPLE_CODE_ID = S.PEOPLE_CODE_ID
			AND TermId BETWEEN @TermId - 1 AND @TermId + 2
		ORDER BY A.TERMID DESC
		) Enrollment
	OUTER APPLY (
		SELECT SUM(CREDITS) [CREDITS]
		FROM [custom].vwACADEMIC A
		WHERE A.PEOPLE_CODE_ID = S.PEOPLE_CODE_ID
			AND A.TermId = @SPTermId
		) AS SP_Credits
	OUTER APPLY (
		SELECT SUM(CREDITS) [CREDITS]
		FROM [custom].vwACADEMIC A
		WHERE A.PEOPLE_CODE_ID = S.PEOPLE_CODE_ID
			AND A.TermId = @SUTermId
		) AS SU_Credits
	OUTER APPLY (
		SELECT SUM(CREDITS) [CREDITS]
		FROM [custom].vwACADEMIC A
		WHERE A.PEOPLE_CODE_ID = S.PEOPLE_CODE_ID
			AND A.TermId = @FATermId
		) AS FA_Credits

	DROP TABLE #Students
END
GO

