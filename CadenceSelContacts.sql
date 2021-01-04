USE [Campus6]
GO

/****** Object:  StoredProcedure [custom].[CadenceSelContacts]    Script Date: 2021-01-04 10:05:34 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


-- =============================================
-- Author:		Wyatt Best
-- Create date: 2020-10-23
-- Description:	Selects three terms' worth of students and various fields to send to Mongoose Cadence.
--
-- 2021-01-04 Wyatt Best: Issue #1: Don't return students with no optedOut state (TELECOMMUNICATIONS record for dept)
-- =============================================
CREATE PROCEDURE [custom].[CadenceSelContacts] @Dept NVARCHAR(2)
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
	SELECT S.PEOPLE_CODE_ID [uniqueCampusId]
		,dbo.fnPeopleOrgName(S.PEOPLE_CODE_ID, 'FN') [firstName]
		,dbo.fnPeopleOrgName(S.PEOPLE_CODE_ID, 'LN') [lastName]
		,Phone.*
		,Enrollment.SHORT_DESC [Enrollment]
		,try_cast(SP_Credits.CREDITS AS INT) [SP_Credits]
		,try_cast(SU_Credits.CREDITS AS INT) [SU_Credits]
		,try_cast(FA_Credits.CREDITS AS INT) [FA_Credits]
		,CASE T.[STATUS]
			WHEN 'A'
				THEN 0
			WHEN 'I'
				THEN 1
			ELSE NULL
			END AS [optedOut]
	FROM #Students S
	OUTER APPLY (
		SELECT TOP 1 CASE 
				WHEN LEFT(PP.PhoneNumber, 1) = '1' --US country code already prepended
					THEN PP.PhoneNumber
				ELSE '1' + PP.PhoneNumber
				END AS [mobileNumber]
		FROM PEOPLE P
		INNER JOIN PersonPhone PP
			ON PP.PersonId = P.PersonId
				AND DoNotCallReason IS NULL
				AND PhoneType = 'MOBILE1'
		WHERE P.PEOPLE_CODE_ID = S.PEOPLE_CODE_ID
			AND CountryId = 240 --US numbers only
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
		SELECT COALESCE(SUM(CREDITS), 0) [CREDITS]
		FROM [custom].vwACADEMIC A
		WHERE A.PEOPLE_CODE_ID = S.PEOPLE_CODE_ID
			AND A.TermId = @SPTermId
		) AS SP_Credits
	OUTER APPLY (
		SELECT COALESCE(SUM(CREDITS), 0) [CREDITS]
		FROM [custom].vwACADEMIC A
		WHERE A.PEOPLE_CODE_ID = S.PEOPLE_CODE_ID
			AND A.TermId = @SUTermId
		) AS SU_Credits
	OUTER APPLY (
		SELECT COALESCE(SUM(CREDITS), 0) [CREDITS]
		FROM [custom].vwACADEMIC A
		WHERE A.PEOPLE_CODE_ID = S.PEOPLE_CODE_ID
			AND A.TermId = @FATermId
		) AS FA_Credits
	INNER JOIN TELECOMMUNICATIONS T
		ON T.PEOPLE_ORG_CODE_ID = S.PEOPLE_CODE_ID
			AND T.COM_TYPE = 'SMS' + @Dept

	DROP TABLE #Students
END
GO

